"""Dream fase 1 — `consolidate` (M3-a).

Estos tests corren con un **modelo falso**: guionan lo que el modelo responde y afirman
qué hace nightshift con eso. El gate de M3-a con el modelo local de verdad es
`nightshift dream --selftest`, que no puede vivir acá porque `make check` tiene que pasar
en una máquina sin ollama.

Lo que se prueba, entonces, no es que el modelo abstraiga bien — eso lo dirá M4 — sino
que nightshift no persista nada que no debería: sin patrón no hay candidate, con una ruta
en el patrón no hay candidate, con el nombre del repo tampoco, y una contradicción enlaza
en vez de borrar.
"""

import contextlib
import io
import json
import os
import shutil
import stat
import subprocess
import tempfile
import unittest
from pathlib import Path

from tests.base import IsolatedStoreTest
from nightshift import cli, config, dream, store

ROOT = Path(__file__).resolve().parent.parent
SCHEMA = ROOT / "schema" / "trajectory.v1.json"

BUENA = {"pattern": "El lector abre el archivo sin declarar codificación y la suite falla "
                    "en el primer byte no ASCII; el fix es declararla explícitamente.",
         "signals": ["la suite falla siempre en el mismo punto"],
         "decisive_signal": "el fallo desaparece al fijar la codificación",
         "hypothesis": "se creyó que el archivo de entrada estaba corrupto",
         "valid_when": ["el archivo de entrada no es ASCII puro"]}


class FakeModel:
    """Modelo guionado. Devuelve las respuestas en orden; la última se repite."""

    name = "fake"

    def __init__(self, *responses):
        self.responses = list(responses)
        self.calls = 0

    def ask_json(self, prompt):
        self.calls += 1
        item = self.responses[min(self.calls - 1, len(self.responses) - 1)]
        if isinstance(item, Exception):
            raise item
        return item


class DreamTest(IsolatedStoreTest):
    def seed(self, conn, *, task_type="debug_test_failure", outcome="tests_passed",
             contradicted=False, summary="la suite falla al leer la entrada"):
        tid = store.open_trajectory(conn, session_id="s", repo_fingerprint="f" * 64,
                                    task_type=task_type, base_commit="abc1234",
                                    redaction={"redactor_version": "0.1.0"})
        store.append_step(conn, tid, kind="tool_failure", tool="run_shell",
                          error_message=summary, decisive=True)
        if contradicted:
            store.mark_last_contradicted(conn, tid)
        store.close_trajectory(conn, tid, result=outcome)
        return tid

    def run_dream(self, model, **kwargs):
        conn = store.connect()
        try:
            return dream.consolidate(conn, model, cfg=config.load(), lookback_days=3650,
                                     **kwargs)
        finally:
            conn.close()

    def row(self, tid):
        conn = store.connect()
        try:
            return store.get_trajectory(conn, tid)
        finally:
            conn.close()

    # ------------------------------------------------------------------ consolidar
    def test_una_cerrada_llega_a_candidate(self):
        conn = store.connect()
        try:
            tid = self.seed(conn)
        finally:
            conn.close()
        report = self.run_dream(FakeModel(BUENA))

        row = self.row(tid)
        self.assertEqual(row["status"], "candidate")
        abstraction = json.loads(row["abstraction_json"])
        self.assertIn("codificación", abstraction["pattern"])
        self.assertEqual(json.loads(row["valid_when_json"])[0]["source"], "inferred")
        self.assertLess(row["injection_weight"], 1.0, "candidate pesa menos que procedure")
        self.assertIsNone(row["verified_json"], "verify es M5 y no existe")
        self.assertEqual(len(report["candidates"]), 1)

    def test_dream_puebla_la_hipotesis_que_la_captura_no_puede(self):
        """`hypothesis` nunca se poblaba: la captura no persiste texto del prompt.

        Dream es el único momento en que puede aparecer, porque la deriva de los pasos.
        Y pasa por los mismos gates que el resto: es texto del modelo.
        """
        conn = store.connect()
        try:
            tid = self.seed(conn)
        finally:
            conn.close()
        self.run_dream(FakeModel(BUENA))
        row = self.row(tid)
        self.assertEqual(row["hypothesis"], "se creyó que el archivo de entrada estaba corrupto")

    def test_una_hipotesis_con_una_ruta_no_se_persiste(self):
        conn = store.connect()
        try:
            tid = self.seed(conn)
        finally:
            conn.close()
        malo = dict(BUENA, hypothesis="se creyó que el bug estaba en /src/parser.py")
        report = self.run_dream(FakeModel(malo))
        self.assertEqual(report["candidates"], [])
        self.assertEqual(self.row(tid)["status"], "closed")
        self.assertTrue(any("hypothesis" in r for r in report["rejected"][0]["reasons"]))

    def test_sin_hipotesis_inferible_no_se_inventa(self):
        conn = store.connect()
        try:
            tid = self.seed(conn)
        finally:
            conn.close()
        sin = dict(BUENA)
        sin.pop("hypothesis")
        self.run_dream(FakeModel(sin))
        row = self.row(tid)
        self.assertEqual(row["status"], "candidate")
        self.assertIsNone(row["hypothesis"])

    def test_no_pisa_una_hipotesis_ya_declarada(self):
        conn = store.connect()
        try:
            tid = store.open_trajectory(conn, session_id="con-hipotesis",
                                        repo_fingerprint="f" * 64,
                                        task_type="debug_test_failure",
                                        hypothesis="la declaró el usuario")
            store.append_step(conn, tid, kind="tool_failure", tool="run_shell",
                              error_message="falla", decisive=True)
            store.close_trajectory(conn, tid, result="tests_passed")
        finally:
            conn.close()
        self.run_dream(FakeModel(BUENA))
        self.assertEqual(self.row(tid)["hypothesis"], "la declaró el usuario")

    def test_agrupa_por_tipo_de_tarea(self):
        """Partir por firma exacta de herramientas dejaba grupos de uno y no consolidaba."""
        conn = store.connect()
        try:
            self.seed(conn, task_type="debug_test_failure")
            self.seed(conn, task_type="debug_test_failure", outcome="user_corrected")
            self.seed(conn, task_type="refactor")
            self.assertEqual([len(g) for g in dream.groups(conn, lookback_days=3650)], [2, 1])
        finally:
            conn.close()

    def test_dry_run_no_escribe(self):
        conn = store.connect()
        try:
            tid = self.seed(conn)
        finally:
            conn.close()
        report = self.run_dream(FakeModel(BUENA), dry_run=True)
        self.assertEqual(len(report["candidates"]), 1)
        self.assertEqual(self.row(tid)["status"], "closed")

    # ---------------------------------------------------- el gate de la capacidad B
    def test_la_contradicha_queda_superseded_y_no_se_borra(self):
        conn = store.connect()
        try:
            vieja = self.seed(conn, outcome="user_corrected", contradicted=True,
                              summary="se cambió el manejo de excepciones y el fallo siguió")
            nueva = self.seed(conn, outcome="tests_passed")
            antes = conn.execute("SELECT COUNT(*) c FROM trajectories").fetchone()["c"]
        finally:
            conn.close()

        report = self.run_dream(FakeModel(BUENA))

        self.assertEqual(self.row(nueva)["status"], "candidate")
        vieja_row = self.row(vieja)
        self.assertEqual(vieja_row["status"], "superseded")
        self.assertEqual(vieja_row["superseded_by"], nueva)
        self.assertEqual([(i["trajectory"], i["by"]) for i in report["superseded"]],
                         [(vieja, nueva)])

        conn = store.connect()
        try:
            self.assertEqual(conn.execute("SELECT COUNT(*) c FROM trajectories").fetchone()["c"],
                             antes, "Auto Dream borra lo contradicho; nosotros lo enlazamos")
            self.assertTrue(store.steps_of(conn, vieja), "los pasos de la vieja siguen ahí")
        finally:
            conn.close()

    # ------------------------------------------------- lo que no se puede persistir
    def test_un_patron_con_ruta_no_se_persiste(self):
        """La red del esquema (spec §4.4). Si el modelo insiste, se descarta el grupo."""
        conn = store.connect()
        try:
            tid = self.seed(conn)
        finally:
            conn.close()
        malo = dict(BUENA, pattern="el bug vive en /src/parser.py y se arregla ahí mismo")
        report = self.run_dream(FakeModel(malo))

        self.assertEqual(self.row(tid)["status"], "closed", "nada se persistió")
        self.assertEqual(report["candidates"], [])
        self.assertEqual(len(report["rejected"]), 1)
        self.assertTrue(any("path" in r for r in report["rejected"][0]["reasons"]))

    def test_el_nombre_del_repo_no_sobrevive_a_la_abstraccion(self):
        """`abstraction` es lo único que cruza de repo A a repo B (capacidad C)."""
        conn = store.connect()
        try:
            tid = self.seed(conn)
        finally:
            conn.close()
        malo = dict(BUENA, pattern="en histora el lector abre sin declarar codificación y "
                                   "la suite falla en el primer byte no ASCII")
        report = self.run_dream(FakeModel(malo), identifiers=["histora"])

        self.assertEqual(self.row(tid)["status"], "closed")
        self.assertTrue(any("redactor" in r for r in report["rejected"][0]["reasons"]))

    def test_un_secreto_en_el_patron_no_se_persiste(self):
        conn = store.connect()
        try:
            self.seed(conn)
        finally:
            conn.close()
        malo = dict(BUENA, pattern="el fix es exportar GITHUB_TOKEN=ghp_abcdefghijklmnop"
                                   "qrstuvwxyz0123 antes de correr la suite entera")
        report = self.run_dream(FakeModel(malo))
        self.assertEqual(report["candidates"], [])
        self.assertEqual(len(report["rejected"]), 1)

    def test_reintenta_y_acepta_la_correccion(self):
        conn = store.connect()
        try:
            tid = self.seed(conn)
        finally:
            conn.close()
        malo = dict(BUENA, pattern="el bug vive en /src/parser.py")
        model = FakeModel(malo, BUENA)
        report = self.run_dream(model)
        self.assertEqual(model.calls, 2)
        self.assertEqual(self.row(tid)["status"], "candidate")
        self.assertEqual(report["rejected"], [])

    def test_sin_patron_comun_no_reintenta_ni_promueve(self):
        """"No hay patrón" es una respuesta legítima. Insistir es pedirle que invente."""
        conn = store.connect()
        try:
            tid = self.seed(conn)
        finally:
            conn.close()
        model = FakeModel({"pattern": None})
        report = self.run_dream(model)
        self.assertEqual(model.calls, 1)
        self.assertEqual(self.row(tid)["status"], "closed")
        self.assertEqual(len(report["skipped"]), 1)
        self.assertEqual(report["rejected"], [])

    def test_un_grupo_roto_no_mata_la_corrida(self):
        conn = store.connect()
        try:
            self.seed(conn, task_type="debug_test_failure")
            bueno = self.seed(conn, task_type="refactor")
        finally:
            conn.close()
        # El primer grupo (debug) rompe en los tres intentos; el segundo responde bien.
        model = FakeModel(dream.DreamError("el modelo no devolvió JSON parseable"),
                          dream.DreamError("idem"), dream.DreamError("idem"), BUENA)
        report = self.run_dream(model)
        self.assertEqual(len(report["rejected"]), 1)
        self.assertEqual(len(report["candidates"]), 1)
        self.assertEqual(self.row(bueno)["status"], "candidate")

    def test_sin_modelo_no_hay_dream_ni_heuristica(self):
        conn = store.connect()
        try:
            tid = self.seed(conn)
        finally:
            conn.close()
        original = dream.detect_command
        dream.detect_command = lambda cfg: None
        try:
            err = io.StringIO()
            with contextlib.redirect_stderr(err), contextlib.redirect_stdout(io.StringIO()):
                code = cli.main(["dream"])
        finally:
            dream.detect_command = original
        self.assertEqual(code, 2, "sin modelo local dream falla y lo dice")
        self.assertIn("no hay modelo local", err.getvalue())
        self.assertIn("no hay fallback remoto", err.getvalue())
        self.assertEqual(self.row(tid)["status"], "closed",
                         "sin modelo no se consolida por heurística")

    def test_un_comando_de_modelo_inexistente_tambien_sale_2(self):
        conn = store.connect()
        try:
            self.seed(conn)
        finally:
            conn.close()
        err = io.StringIO()
        with contextlib.redirect_stderr(err), contextlib.redirect_stdout(io.StringIO()):
            code = cli.main(["dream", "--model", "/nonexistent/qwen-que-no-esta"])
        self.assertEqual(code, 2)

    def test_sin_nada_que_consolidar_no_es_un_fallo(self):
        out, err = io.StringIO(), io.StringIO()
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
            code = cli.main(["dream", "--model", "/bin/echo"])
        self.assertEqual(code, 0, "una noche sin trayectorias nuevas no es un error")
        self.assertIn("nada que consolidar", err.getvalue())

    def test_sin_patron_comun_es_una_noche_tranquila_no_un_fallo(self):
        """Salir 1 acá haría figurar una noche normal como corrida fallida.

        Y entonces el gate de M3 —tres noches seguidas sin intervención— no podría
        distinguir una noche tranquila de una que hay que ir a mirar. Lo encontró el
        ensayo end-to-end, no una revisión.
        """
        conn = store.connect()
        try:
            self.seed(conn)
        finally:
            conn.close()
        original = dream.detect_command
        dream.detect_command = lambda cfg: None
        try:
            out, err = io.StringIO(), io.StringIO()
            with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
                code = cli.main(["dream", "--model", "/bin/echo"])
        finally:
            dream.detect_command = original
        self.assertEqual(code, 1, "/bin/echo no devuelve JSON: eso es un grupo descartado")

        # Y ahora el caso real: el modelo responde bien y dice que no hay patrón.
        original_consolidate = dream.consolidate
        dream.consolidate = lambda conn_, model, **kw: {
            "model": "fake", "lookback_days": 7, "groups": 1, "trajectories": 1,
            "candidates": [], "superseded": [], "rejected": [],
            "skipped": [{"trajectory": "x", "reason": dream.SIN_PATRON}], "dry_run": False}
        try:
            out, err = io.StringIO(), io.StringIO()
            with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
                code = cli.main(["dream", "--model", "/bin/echo"])
        finally:
            dream.consolidate = original_consolidate
        self.assertEqual(code, 0, "«no comparten patrón» es una respuesta, no un fallo")
        self.assertIn("no encontró patrón común", err.getvalue())

        conn = store.connect()
        try:
            self.assertIn("noche tranquila", store.recent_runs(conn)[0]["note"])
        finally:
            conn.close()

    def test_con_material_y_sin_candidatas_sale_distinto_de_cero(self):
        conn = store.connect()
        try:
            self.seed(conn)
        finally:
            conn.close()
        # `/bin/echo` devuelve el prompt: no es JSON, así que el grupo se descarta.
        out, err = io.StringIO(), io.StringIO()
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
            code = cli.main(["dream", "--model", "/bin/echo"])
        self.assertEqual(code, 1, "un consolidate que no consolidó no puede salir 0")

    def test_no_lista_como_candidata_lo_que_no_se_promovio(self):
        """La promoción exige `closed`. Un reporte que igual la lista es un reporte que miente."""
        conn = store.connect()
        try:
            tid = self.seed(conn)
            # Alguien la movió entre que se agrupó y que se iba a promover.
            original = store.promote_to_candidate

            def sabotaje(conn_, trajectory_id, **kwargs):
                conn_.execute("UPDATE trajectories SET status = 'discarded' WHERE id = ?",
                              (trajectory_id,))
                conn_.commit()
                return original(conn_, trajectory_id, **kwargs)
        finally:
            conn.close()

        store.promote_to_candidate = sabotaje
        try:
            report = self.run_dream(FakeModel(BUENA))
        finally:
            store.promote_to_candidate = original

        self.assertEqual(report["candidates"], [], "no se promovió: no se lista")
        self.assertEqual(len(report["rejected"]), 1)
        self.assertIn("no se aplicó", report["rejected"][0]["reasons"][0])
        self.assertEqual(self.row(tid)["status"], "discarded")

    def test_why_reconstruye_el_origen_de_una_candidata(self):
        """Condición de éxito 3: una candidata se inyecta por su patrón, no por sus pasos."""
        conn = store.connect()
        try:
            vieja = self.seed(conn, outcome="user_corrected", contradicted=True)
            nueva = self.seed(conn, outcome="tests_passed")
        finally:
            conn.close()
        self.run_dream(FakeModel(BUENA))

        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            self.assertEqual(cli.main(["why", nueva[:8]]), 0)
        texto = out.getvalue()
        self.assertIn("abstracción", texto)
        self.assertIn("codificación", texto, "el patrón por el que se inyectaría")
        self.assertIn("aplica cuando", texto)
        self.assertIn("contradice a 1", texto)
        self.assertIn(vieja[:8], texto)

        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            cli.main(["why", vieja[:8]])
        texto = out.getvalue()
        self.assertIn("sobrevive enlazada, no se borró", texto)
        self.assertIn(nueva[:8], texto)

    # ------------------------------------------------- la salida cruda del modelo
    def test_extrae_json_entre_prosa(self):
        self.assertEqual(dream.extract_json('bla bla {"pattern": "x"} y más bla'),
                         {"pattern": "x"})
        self.assertEqual(dream.extract_json("Thinking...\n{}\n"), {})
        self.assertEqual(dream.extract_json("<think>mmm</think>{\"a\": 1}"), {"a": 1})
        self.assertIsNone(dream.extract_json("no hay json acá"))

    def test_deshace_el_reacomodo_de_palabras_de_ollama(self):
        """Hallazgo de correr el modelo: ollama re-envuelve aunque stdout sea un pipe.

        Emite el fragmento, vuelve el cursor con `ESC[nD` y reescribe la palabra en la
        línea siguiente. Borrar los escapes a secas deja `parpartido` y un salto de línea
        dentro de un string: JSON inválido.
        """
        crudo = '{"pattern": "queda par\x1b[3D\x1b[K\npartido al medio"}'
        self.assertEqual(dream.extract_json(crudo), {"pattern": "queda partido al medio"})

    # ------------------------------------------------------------------ backends
    def test_el_default_es_claude_code(self):
        """ADR-003: el agente que ya está instalado y autenticado, por `subprocess`."""
        comando = dream.detect_command({})
        self.assertIsNotNone(comando, "hace falta `claude` en el PATH para este test")
        self.assertIn("claude", comando[0])
        self.assertIn("-p", comando)
        self.assertIn("--output-format", comando)

    def test_el_backend_local_sigue_disponible(self):
        """Para un repo cuyo material no puede salir de la máquina, es una línea de config."""
        comando = dream.detect_command({"model_backend": "local"})
        if comando is None:
            self.skipTest("ollama no está en esta máquina")
        self.assertIn("ollama", comando[0])

    def test_el_modelo_concreto_no_se_elige_solo(self):
        """Elegirlo sería fijar una constante del experimento (PREREG §2)."""
        self.assertNotIn("--model", dream.detect_command({}))
        self.assertIn("sonnet", dream.detect_command({"model_name": "sonnet"}))

    def test_desenvuelve_la_respuesta_del_agente(self):
        """Un agente no interactivo devuelve un envoltorio con la respuesta adentro.

        Quedarse con el envoltorio sería leer la factura en vez de la respuesta.
        """
        envoltorio = json.dumps({
            "is_error": False, "num_turns": 1, "total_cost_usd": 0.19,
            "result": 'Acá va: {"pattern": "el patrón de verdad", "signals": []}',
        })
        self.assertEqual(dream.extract_json(envoltorio),
                         {"pattern": "el patrón de verdad", "signals": []})

    def test_un_json_directo_sigue_funcionando(self):
        self.assertEqual(dream.extract_json('{"pattern": "directo"}'),
                         {"pattern": "directo"})

    def test_un_envoltorio_sin_json_adentro_se_devuelve_entero(self):
        crudo = json.dumps({"result": "no hay json acá", "num_turns": 1})
        self.assertEqual(dream.extract_json(crudo)["result"], "no hay json acá")

    def test_el_modelo_corre_con_un_home_desechable(self):
        """Sin esto, consolidar capturaría su propia sesión en el store que consolida.

        El backend nuevo es un agente con los hooks de nightshift disponibles. El hijo
        corre con `NIGHTSHIFT_HOME` temporal, y sin config ahí la captura ni arranca.
        """
        import os
        import tempfile

        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        sonda = Path(tmp.name) / "sonda.sh"
        salida = Path(tmp.name) / "visto.txt"
        sonda.write_text('#!/bin/sh\nprintf "%%s" "$NIGHTSHIFT_HOME" > %s\n'
                         'echo \'{"pattern": null}\'\n' % salida, encoding="utf-8")
        sonda.chmod(0o755)

        propio = os.environ.get("NIGHTSHIFT_HOME")
        dream.LocalModel([str(sonda)], timeout=30).ask("hola")
        visto = salida.read_text(encoding="utf-8")

        self.assertTrue(visto, "el hijo tiene que ver un NIGHTSHIFT_HOME")
        self.assertNotEqual(visto, propio,
                            "el modelo no puede escribir en el store que está consolidando")
        self.assertFalse(Path(visto).exists(), "y era temporal: ya no está")

    def test_elige_el_qwen_mas_chico_y_no_descarga_nada(self):
        """El target es una Air de noche, no una workstation."""
        tmp = tempfile.mkdtemp(prefix="ns-ollama-")
        fake = Path(tmp) / "ollama"
        fake.write_text("#!/bin/sh\n"
                        "printf 'NAME\\tID\\nqwen3.5:9b x\\nllama3:8b y\\nqwen3.5:4b z\\n'\n",
                        encoding="utf-8")
        fake.chmod(fake.stat().st_mode | stat.S_IEXEC)
        saved = os.environ["PATH"]
        os.environ["PATH"] = tmp
        try:
            command = dream.detect_command({"model_backend": "local"})
            self.assertIsNotNone(command)
            self.assertIn("qwen3.5:4b", command)
            self.assertNotIn("pull", command, "autodetectar no puede bajarse un modelo")
        finally:
            os.environ["PATH"] = saved
            shutil.rmtree(tmp, ignore_errors=True)

    def test_sin_ningun_ejecutable_no_hay_comando(self):
        tmp = tempfile.mkdtemp(prefix="ns-vacio-")
        saved = os.environ["PATH"]
        os.environ["PATH"] = tmp
        try:
            self.assertIsNone(dream.detect_command({}))
            self.assertIsNone(dream.detect_command({"model_backend": "local"}))
        finally:
            os.environ["PATH"] = saved
            shutil.rmtree(tmp, ignore_errors=True)

    def test_la_config_manda_sobre_la_autodeteccion(self):
        self.assertEqual(dream.detect_command({"model_command": ["mi-modelo", "--x"]}),
                         ["mi-modelo", "--x"])

    # ------------------------------------------------------------------- esquema
    def test_una_candidate_valida_contra_el_esquema(self):
        from tests.test_schema_roundtrip import validator

        cmd = validator()
        if cmd is None:
            self.skipTest("check-jsonschema no disponible")
        conn = store.connect()
        try:
            vieja = self.seed(conn, outcome="user_corrected", contradicted=True)
            nueva = self.seed(conn, outcome="tests_passed")
        finally:
            conn.close()
        self.run_dream(FakeModel(BUENA))

        conn = store.connect()
        try:
            docs = [store.export_trajectory(conn, tid) for tid in (nueva, vieja)]
        finally:
            conn.close()
        self.assertEqual([d["status"] for d in docs], ["candidate", "superseded"])
        for doc in docs:
            with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False,
                                             encoding="utf-8") as handle:
                json.dump(doc, handle, ensure_ascii=False)
                path = handle.name
            try:
                result = subprocess.run(cmd + ["--schemafile", str(SCHEMA), path],
                                        capture_output=True, text=True, timeout=300)
                self.assertEqual(result.returncode, 0,
                                 "%s no valida:\n%s%s" % (doc["status"], result.stdout,
                                                          result.stderr))
            finally:
                Path(path).unlink(missing_ok=True)


if __name__ == "__main__":
    unittest.main()
