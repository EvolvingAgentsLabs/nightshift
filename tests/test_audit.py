"""`nightshift audit` — el gate de M1.

Dos afirmaciones, y la segunda es la que importa:

1. sobre un store limpio no hay hallazgos;
2. sobre un store al que se le **siembra** una fuga a mano, `audit` la encuentra.

Un auditor que nunca falla no es un auditor: cada clase de fuga que el reporte dice
buscar tiene acá un caso que la siembra y falla si el chequeo se cae.

El tercer eje es el del reporte: hay un test de que el valor filtrado **no** aparece en
la salida, ni en texto ni en `--json`.
"""

import contextlib
import io
import json
import unittest
from pathlib import Path

from tests.base import IsolatedStoreTest
from nightshift import audit, cli, config, store
from nightshift.redact import Redactor

REPO_ROOT = Path(__file__).resolve().parent.parent

SECRET = "ghp_abcdefghijklmnopqrstuvwxyz0123"
DENIED = "/home/matias/proyecto/.env"
HOME_PATH = "/Users/matias/proyectos/x/parser.py"


class AuditTest(IsolatedStoreTest):
    def redactor(self):
        return Redactor(deny_paths=config.load()["deny_paths"], home_dir="/home/matias")

    def seed(self, conn, *, session_id="s1", **step):
        tid = store.open_trajectory(conn, session_id=session_id, repo_fingerprint="a" * 64,
                                    task_type="debug_test_failure", base_commit="abc1234",
                                    redaction={"redactor_version": "0.1.0"})
        store.append_step(conn, tid, kind="tool_use", tool="read_file", tool_native="Read",
                          **step)
        return tid

    def audit(self, conn):
        return audit.audit_store(conn, redactor=self.redactor(), home_dir="/home/matias")

    def rules(self, report):
        return {f["rule"] for f in report["findings"]}

    # ------------------------------------------------------------------ limpio
    def test_store_limpio_no_tiene_hallazgos(self):
        conn = store.connect()
        try:
            tid = self.seed(conn, args={"file_path": "<PATH>"},
                            result_summary="3 tests fallan en <PATH>")
            store.close_trajectory(conn, tid, result="tests_passed")
            store.record_injection(conn, session_id="s1", source_trajectory=tid, rank=1,
                                   score=0.9, reason="same_task_type,same_repo")
            report = self.audit(conn)
            self.assertEqual(report["findings"], [])
            self.assertEqual(report["sessions"], 1)
            self.assertEqual(report["trajectories"], 1)
            self.assertEqual(report["steps"], 1)
            self.assertEqual(report["injections"], 1)
            self.assertGreater(report["fields_scanned"], 0)
        finally:
            conn.close()

    def test_lo_que_el_redactor_dejo_no_es_hallazgo(self):
        """`API_TOKEN=<SECRET>` es la prueba de que la regla corrió, no una fuga."""
        conn = store.connect()
        try:
            self.seed(conn, args={"command": "pytest -q", "env": {"API_TOKEN": "<SECRET>"}},
                      result_summary='API_TOKEN="<SECRET>" en <PATH>, mail <EMAIL>')
            self.assertEqual(self.audit(conn)["findings"], [])
        finally:
            conn.close()

    # --------------------------------------------------------------- sembradas
    def test_encuentra_una_fuga_de_deny_path(self):
        conn = store.connect()
        try:
            tid = self.seed(conn, args={"file_path": DENIED})
            report = self.audit(conn)
            self.assertIn("deny_path", self.rules(report))
            leak = [f for f in report["findings"] if f["rule"] == "deny_path"][0]
            self.assertEqual(leak["trajectory"], tid)
            self.assertEqual(leak["step"], 0)
            self.assertEqual(leak["field"], "steps[0].args_redacted.file_path")
        finally:
            conn.close()

    def test_encuentra_una_fuga_de_deny_path_embebida_en_prosa(self):
        """`fnmatch` compara la cadena entera: sin tokenizar, esto no matchearía nada."""
        conn = store.connect()
        try:
            self.seed(conn, result_summary="abrí %s y decía DB_URL" % DENIED)
            self.assertIn("deny_path", self.rules(self.audit(conn)))
        finally:
            conn.close()

    def test_una_mencion_no_es_una_ruta(self):
        """El límite del chequeo anterior, fijado porque se cruzó una vez.

        `.env` escrito en un comentario es una mención; sin esta línea el auditor marca
        su propio código fuente capturado y nunca puede salir 0. Un valor que *es* la
        ruta se sigue detectando: eso lo prueban los dos casos de arriba.
        """
        conn = store.connect()
        try:
            self.seed(conn, args={"content": "# .env, .npmrc y credentials, en un comentario"})
            self.assertEqual(self.audit(conn)["findings"], [])
        finally:
            conn.close()

    def test_un_valor_que_es_la_ruta_negada_se_detecta_igual(self):
        conn = store.connect()
        try:
            self.seed(conn, args={"file_path": ".env"})
            self.assertIn("deny_path", self.rules(self.audit(conn)))
        finally:
            conn.close()

    def test_encuentra_un_secreto_que_el_redactor_dejo_pasar(self):
        conn = store.connect()
        try:
            self.seed(conn, result_summary="el token es %s" % SECRET)
            report = self.audit(conn)
            self.assertIn("secret.github", self.rules(report))
            leak = [f for f in report["findings"] if f["rule"] == "secret.github"][0]
            self.assertEqual(leak["field"], "steps[0].result_summary")
        finally:
            conn.close()

    def test_encuentra_una_ruta_absoluta_del_home(self):
        conn = store.connect()
        try:
            self.seed(conn, error_message="no pude leer %s" % HOME_PATH)
            self.assertIn("home_path", self.rules(self.audit(conn)))
        finally:
            conn.close()

    def test_encuentra_el_arbol_de_auto_memory(self):
        """Coexistencia (spec §1.3.4): nada del árbol nativo puede haberse persistido."""
        conn = store.connect()
        try:
            self.seed(conn, result_summary="leí ~/.claude/projects/foo/memory/MEMORY.md")
            self.assertIn("auto_memory", self.rules(self.audit(conn)))
        finally:
            conn.close()

    def test_encuentra_un_path_en_abstraction_pattern(self):
        """La red que el esquema tiende bajo dream (M3): un patrón no lleva rutas."""
        conn = store.connect()
        try:
            tid = self.seed(conn, result_summary="ok")
            conn.execute("UPDATE trajectories SET abstraction_json = ? WHERE id = ?",
                         (json.dumps({"pattern": "el fix vive en ../src/parser.py"}), tid))
            conn.commit()
            report = self.audit(conn)
            self.assertIn("abstraction_path", self.rules(report))
            leak = [f for f in report["findings"] if f["rule"] == "abstraction_path"][0]
            self.assertEqual(leak["field"], "trajectory.abstraction.pattern")
        finally:
            conn.close()

    def test_encuentra_una_fuga_en_una_clave_de_diccionario(self):
        """Una clave puede ser el material: se audita, pero no se imprime como campo."""
        conn = store.connect()
        try:
            self.seed(conn, args={DENIED: "contenido"})
            report = self.audit(conn)
            self.assertIn("deny_path", self.rules(report))
            for item in report["findings"]:
                self.assertNotIn(".env", item["field"])
                self.assertIn("<clave>", item["field"])
        finally:
            conn.close()

    # ------------------------------------------------------------------ reporte
    def test_el_reporte_dice_donde_pero_no_que(self):
        conn = store.connect()
        try:
            self.seed(conn, args={"file_path": DENIED}, result_summary="token %s" % SECRET,
                      error_message="no pude leer %s" % HOME_PATH)
        finally:
            conn.close()

        for argv in (["audit"], ["audit", "--json"]):
            with self.subTest(argv=argv):
                out = io.StringIO()
                with contextlib.redirect_stdout(out):
                    code = cli.main(argv)
                text = out.getvalue()
                self.assertEqual(code, 1)
                for value in (SECRET, DENIED, HOME_PATH, ".env", "matias"):
                    self.assertNotIn(value, text)
                self.assertIn("deny_path", text)
                self.assertIn("secret.github", text)
                self.assertIn("home_path", text)
                self.assertIn("steps[0].result_summary", text)

    def test_json_es_parseable_y_no_trae_valores(self):
        conn = store.connect()
        try:
            self.seed(conn, result_summary="token %s" % SECRET)
        finally:
            conn.close()
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            cli.main(["audit", "--json"])
        report = json.loads(out.getvalue())
        self.assertFalse(report["ok"])
        self.assertEqual(sorted(report["findings"][0]),
                         ["field", "len", "pos", "rule", "step", "trajectory"])

    # -------------------------------------------------------------- min-sessions
    def test_min_sessions_decide_el_codigo_de_salida(self):
        conn = store.connect()
        try:
            self.seed(conn, session_id="s1", result_summary="ok")
            self.seed(conn, session_id="s2", result_summary="ok")
        finally:
            conn.close()
        for minimum, expected in ((0, 0), (2, 0), (5, 1)):
            with self.subTest(min_sessions=minimum):
                out = io.StringIO()
                with contextlib.redirect_stdout(out):
                    code = cli.main(["audit", "--min-sessions", str(minimum)])
                self.assertEqual(code, expected)

    def test_sin_config_no_hay_contra_que_auditar(self):
        config.config_path().unlink()
        err = io.StringIO()
        with contextlib.redirect_stderr(err):
            self.assertEqual(cli.main(["audit"]), 1)
        self.assertIn("nightshift init", err.getvalue())

    # ------------------------------------------------------------------- doctor
    def test_el_doctor_afirma_que_el_store_no_tiene_fugas(self):
        """El gate de M1 también como invariante de runtime, no sólo como reporte."""
        conn = store.connect()
        try:
            self.seed(conn, result_summary="todo redactado: <PATH> y <SECRET>")
        finally:
            conn.close()
        nombres = {c["name"]: c for c in cli.run_doctor()}
        self.assertIn("store sin fugas (audit)", nombres)
        self.assertTrue(nombres["store sin fugas (audit)"]["ok"])

        conn = store.connect()
        try:
            self.seed(conn, session_id="s2", result_summary="el token es %s" % SECRET)
        finally:
            conn.close()
        nombres = {c["name"]: c for c in cli.run_doctor()}
        self.assertFalse(nombres["store sin fugas (audit)"]["ok"])
        self.assertNotIn(SECRET, nombres["store sin fugas (audit)"]["detail"],
                         "ni el doctor imprime el valor")

    def test_el_doctor_falla_si_la_captura_de_ahora_llega_vacia(self):
        conn = store.connect()
        try:
            tid = store.open_trajectory(conn, session_id="hueca",
                                        repo_fingerprint="f" * 64, task_type="general")
            for _ in range(4):
                store.append_step(conn, tid, kind="tool_use", tool="run_shell")
        finally:
            conn.close()
        nombres = {c["name"]: c for c in cli.run_doctor()}
        self.assertIn("la captura trae contenido", nombres)
        self.assertFalse(nombres["la captura trae contenido"]["ok"],
                         "cuatro pasos y ninguno con contenido es la captura rota")

    # --------------------------------------------------------------- invariantes
    def test_el_patron_de_abstraction_sigue_al_esquema(self):
        """Si el esquema cambia su red contra paths, este módulo se entera acá."""
        schema = json.loads((REPO_ROOT / "schema" / "trajectory.v1.json").read_text("utf-8"))
        pattern = schema["properties"]["abstraction"]["properties"]["pattern"]["not"]["pattern"]
        self.assertEqual(pattern, audit.ABSTRACTION_PATH_PATTERN)


if __name__ == "__main__":
    unittest.main()
