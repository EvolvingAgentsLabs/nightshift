"""El store persiste y exporta en el formato que M0 congeló."""

import unittest

from tests.base import IsolatedStoreTest
from nightshift import store


class StoreTest(IsolatedStoreTest):
    def test_ciclo_de_vida(self):
        conn = store.connect()
        try:
            tid = store.open_trajectory(conn, session_id="s1", repo_fingerprint="a" * 64,
                                        task_type="debug_test_failure", base_commit="abc1234",
                                        redaction={"redactor_version": "0.1.0"})
            self.assertEqual(store.active_trajectory(conn, "s1")["id"], tid)

            store.append_step(conn, tid, kind="tool_use", tool="run_shell", tool_native="Bash",
                              result_summary="3 tests fallan")
            store.append_step(conn, tid, kind="tool_failure", tool="run_shell",
                              error_message="UnicodeDecodeError", decisive=True)
            self.assertEqual(len(store.steps_of(conn, tid)), 2)

            self.assertEqual(store.mark_last_contradicted(conn, tid), 1)
            self.assertTrue(store.steps_of(conn, tid)[1]["contradicted"])

            status = store.close_trajectory(conn, tid, result="tests_passed", gate_id="make-check")
            self.assertEqual(status, "closed")
            self.assertIsNone(store.active_trajectory(conn, "s1"))
        finally:
            conn.close()

    def test_abandoned_va_a_discarded(self):
        conn = store.connect()
        try:
            tid = store.open_trajectory(conn, session_id="s2", repo_fingerprint="b" * 64,
                                        task_type="general")
            self.assertEqual(store.close_trajectory(conn, tid, result="abandoned"), "discarded")
        finally:
            conn.close()

    def test_max_steps_frena(self):
        conn = store.connect()
        try:
            tid = store.open_trajectory(conn, session_id="s3", repo_fingerprint="c" * 64,
                                        task_type="general")
            for _ in range(5):
                store.append_step(conn, tid, kind="tool_use", max_steps=3)
            self.assertEqual(len(store.steps_of(conn, tid)), 3)
        finally:
            conn.close()

    def test_pasos_concurrentes_no_se_pisan(self):
        """El bug que encontró correr el benchmark: dos hooks a la vez perdían un paso.

        Claude Code lanza tool calls en paralelo, y cada hook es un proceso nuevo con su
        propia conexión. Con el índice calculado en dos sentencias, los dos leían el
        mismo máximo y el segundo moría con `UNIQUE constraint failed`. El hook salía 0
        igual —como manda spec §7.2— así que la sesión no se enteraba de nada.
        """
        import threading

        conn = store.connect()
        try:
            tid = store.open_trajectory(conn, session_id="paralelo",
                                        repo_fingerprint="a" * 64, task_type="general")
        finally:
            conn.close()

        errores, indices = [], []
        cerrojo = threading.Lock()

        def agregar(n):
            propia = store.connect()
            try:
                idx = store.append_step(propia, tid, kind="tool_use", tool="run_shell",
                                        result_summary="paso %d" % n)
                with cerrojo:
                    indices.append(idx)
            except Exception as exc:            # noqa: BLE001 - se reporta, no se traga
                with cerrojo:
                    errores.append(repr(exc))
            finally:
                propia.close()

        hilos = [threading.Thread(target=agregar, args=(n,)) for n in range(12)]
        for hilo in hilos:
            hilo.start()
        for hilo in hilos:
            hilo.join()

        self.assertEqual(errores, [], "ningún hook puede morir por una carrera")
        conn = store.connect()
        try:
            pasos = store.steps_of(conn, tid)
        finally:
            conn.close()
        self.assertEqual(len(pasos), 12, "no se perdió ningún paso")
        self.assertEqual(sorted(p["idx"] for p in pasos), list(range(12)),
                         "los índices son consecutivos y únicos")

    def test_el_tope_de_pasos_tambien_es_atomico(self):
        conn = store.connect()
        try:
            tid = store.open_trajectory(conn, session_id="tope", repo_fingerprint="b" * 64,
                                        task_type="general")
            for _ in range(6):
                store.append_step(conn, tid, kind="tool_use", max_steps=4)
            self.assertEqual(len(store.steps_of(conn, tid)), 4)
            self.assertIsNone(store.append_step(conn, tid, kind="tool_use", max_steps=4))
        finally:
            conn.close()

    def test_la_calidad_de_captura_ve_una_trayectoria_hueca(self):
        """El check que faltaba: pasos capturados sin una línea de contenido.

        Es exactamente lo que pasó durante M1 y M2 —223 pasos de cáscara— sin que nada
        lo dijera, porque los hooks salen 0 pase lo que pase.
        """
        conn = store.connect()
        try:
            hueca = store.open_trajectory(conn, session_id="hueca",
                                          repo_fingerprint="a" * 64, task_type="general")
            for _ in range(4):
                store.append_step(conn, hueca, kind="tool_use", tool="run_shell")
            calidad = store.capture_quality(conn)
            self.assertEqual(calidad["tool_steps"], 4)
            self.assertEqual(calidad["hollow"], 4)
            self.assertEqual(calidad["hollow_ratio"], 1.0)
            self.assertIn(hueca, calidad["broken"])
            self.assertFalse(calidad["latest"]["healthy"])
        finally:
            conn.close()

    def test_la_calidad_no_promedia_entre_cohortes_de_captura(self):
        """El 52% que reportaba el store real era un promedio entre generaciones.

        Mezclaba trayectorias escritas antes y después del arreglo de los campos del
        payload mientras la última iba 1 de 52. Una alarma que suena para siempre es donde
        se esconde la regresión siguiente.
        """
        conn = store.connect()
        try:
            vieja = store.open_trajectory(conn, session_id="vieja",
                                          repo_fingerprint="a" * 64, task_type="general")
            for _ in range(10):
                store.append_step(conn, vieja, kind="tool_use", tool="run_shell")
            # Como si la hubiera escrito el código de captura anterior a la cohorte.
            conn.execute("UPDATE trajectories SET capture_cohort = NULL WHERE id = ?",
                         (vieja,))
            conn.commit()

            nueva = store.open_trajectory(conn, session_id="nueva",
                                          repo_fingerprint="a" * 64, task_type="general")
            for i in range(4):
                store.append_step(conn, nueva, kind="tool_use", tool="run_shell",
                                  result_summary="contenido %d" % i)

            calidad = store.capture_quality(conn)
            self.assertEqual(calidad["tool_steps"], 4, "los 10 pasos viejos no se cuentan")
            self.assertEqual(calidad["hollow"], 0)
            self.assertEqual(calidad["other_cohorts"], 1)
            self.assertNotIn(vieja, calidad["broken"],
                             "una trayectoria de otra cohorte no es la captura de ahora")
        finally:
            conn.close()

    def test_una_trayectoria_nueva_declara_su_cohorte(self):
        conn = store.connect()
        try:
            tid = store.open_trajectory(conn, session_id="s", repo_fingerprint="a" * 64,
                                        task_type="general")
            fila = store.get_trajectory(conn, tid)
            self.assertEqual(fila["capture_cohort"], store.COHORTE_DE_CAPTURA)
        finally:
            conn.close()

    def test_una_trayectoria_vieja_rota_no_deja_el_doctor_en_rojo_para_siempre(self):
        """`status` cuenta la historia; el doctor afirma sobre el presente."""
        conn = store.connect()
        try:
            vieja = store.open_trajectory(conn, session_id="vieja",
                                          repo_fingerprint="a" * 64, task_type="general")
            for _ in range(4):
                store.append_step(conn, vieja, kind="tool_use", tool="run_shell")
            store.close_trajectory(conn, vieja, result="unknown")

            nueva = store.open_trajectory(conn, session_id="nueva",
                                          repo_fingerprint="a" * 64, task_type="general")
            for i in range(4):
                store.append_step(conn, nueva, kind="tool_use", tool="run_shell",
                                  result_summary="salida %d" % i)

            calidad = store.capture_quality(conn)
            self.assertIn(vieja, calidad["broken"], "la historia se sigue contando")
            self.assertEqual(calidad["latest"]["trajectory"], nueva)
            self.assertTrue(calidad["latest"]["healthy"], "y el presente está sano")
        finally:
            conn.close()

    def test_dos_trayectorias_del_mismo_segundo_tienen_orden_definido(self):
        """Las marcas de tiempo son de segundos: sin desempate, "la última" es la que quiera.

        Lo encontró el test de arriba abriendo dos trayectorias seguidas. Afecta a todo
        lo que ordena por `created_at`: cuál es la trayectoria activa de una sesión, cuál
        es la última capturada, y en qué orden dream agrupa.
        """
        conn = store.connect()
        try:
            ids = [store.open_trajectory(conn, session_id="mismo-segundo",
                                         repo_fingerprint="a" * 64, task_type="general")
                   for _ in range(5)]
            marcas = {r["created_at"] for r in
                      conn.execute("SELECT created_at FROM trajectories")}
            self.assertEqual(len(marcas), 1, "las cinco caen en el mismo segundo")
            self.assertEqual(store.active_trajectory(conn, "mismo-segundo")["id"], ids[-1],
                             "la activa es la última abierta, no una cualquiera")
            for _ in range(3):
                store.append_step(conn, ids[-1], kind="tool_use", tool="run_shell",
                                  result_summary="con contenido")
            self.assertEqual(store.capture_quality(conn)["latest"]["trajectory"], ids[-1])
        finally:
            conn.close()

    def test_sin_pasos_de_tool_no_hay_veredicto(self):
        conn = store.connect()
        try:
            calidad = store.capture_quality(conn)
            self.assertIsNone(calidad["latest"])
            self.assertEqual(calidad["tool_steps"], 0)
        finally:
            conn.close()

    def test_un_store_viejo_se_migra_sin_perder_nada(self):
        """`CREATE TABLE IF NOT EXISTS` no toca una tabla que ya existe.

        Sin migración, un store creado antes de que `runs` tuviera `cost_usd` se queda sin
        la columna para siempre y falla al escribir. Migrar es agregar lo que falte: nunca
        borrar ni reescribir una columna con datos.
        """
        import re
        import sqlite3

        from nightshift import config

        db = config.db_path()
        viejo = store.SCHEMA_SQL.replace("    cost_usd REAL,\n", "")
        tabla_runs = re.search(r"CREATE TABLE IF NOT EXISTS runs \(.*?\);", viejo, re.S).group(0)
        self.assertNotIn("cost_usd", tabla_runs, "el esquema viejo no tenía la columna")
        conn = sqlite3.connect(str(db))
        conn.executescript(viejo)
        conn.execute("INSERT INTO runs (started_at, command, exit_code, note)"
                     " VALUES ('2026-01-01T00:00:00Z','dream',0,'corrida vieja')")
        conn.commit()
        conn.close()

        conn = store.connect()
        try:
            columnas = {f["name"] for f in conn.execute("PRAGMA table_info(runs)")}
            self.assertIn("cost_usd", columnas, "la migración agregó la columna")
            vieja = conn.execute("SELECT note, cost_usd FROM runs").fetchone()
            self.assertEqual(vieja["note"], "corrida vieja", "y no perdió la fila")
            self.assertIsNone(vieja["cost_usd"])

            store.record_run(conn, command="dream", exit_code=0, cost_usd=0.42)
            nueva = store.recent_runs(conn)[0]
            self.assertEqual(nueva["cost_usd"], 0.42)
        finally:
            conn.close()

    def test_migrar_dos_veces_no_rompe_nada(self):
        conn = store.connect()
        try:
            self.assertEqual(store.migrate(conn), [], "ya está migrado: no hay nada que hacer")
        finally:
            conn.close()

    def test_export_tiene_la_forma_del_schema(self):
        conn = store.connect()
        try:
            tid = store.open_trajectory(conn, session_id="s4", repo_fingerprint="d" * 64,
                                        task_type="general", base_commit="abc1234",
                                        redaction={"redactor_version": "0.1.0"})
            store.append_step(conn, tid, kind="tool_use", tool="read_file")
            store.close_trajectory(conn, tid, result="unknown")
            doc = store.export_trajectory(conn, tid)
            self.assertEqual(doc["schema_version"], "trajectory.v1")
            for field in ("id", "created_at", "status", "harness", "repo_fingerprint",
                          "task_type", "steps", "redaction"):
                self.assertIn(field, doc)
            self.assertEqual(doc["steps"][0]["index"], 0)
        finally:
            conn.close()

    def test_prefijo_de_id_resuelve(self):
        conn = store.connect()
        try:
            tid = store.open_trajectory(conn, session_id="s5", repo_fingerprint="e" * 64,
                                        task_type="general")
            self.assertEqual(store.get_trajectory(conn, tid[:8])["id"], tid)
        finally:
            conn.close()

    def test_store_size_bytes_crece_con_datos_y_cuenta_el_wal(self):
        conn = store.connect()
        try:
            antes = store.store_size_bytes()
            self.assertGreater(antes, 0)  # el archivo ya existe por connect()

            tid = store.open_trajectory(conn, session_id="s6", repo_fingerprint="f" * 64,
                                        task_type="general")
            for _ in range(50):
                store.append_step(conn, tid, kind="tool_use", tool="read_file",
                                  result_summary="x" * 500)

            # sin checkpointear: si store_size_bytes() no sumara el -wal, este assert
            # fallaría porque los datos recién escritos viven ahí, no en el archivo
            # principal.
            despues = store.store_size_bytes()
            self.assertGreater(despues, antes)
        finally:
            conn.close()

    def test_store_size_bytes_cero_sin_store(self):
        self.assertEqual(store.store_size_bytes(self.home / "no-existe.sqlite3"), 0)


if __name__ == "__main__":
    unittest.main()
