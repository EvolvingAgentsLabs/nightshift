"""Retrieval e inyección (M2), y el gate de M2: `why` reconstruye el origen."""

import unittest

from tests.base import IsolatedStoreTest
from nightshift import config, hook, retrieve, store

FP = "f" * 64


class RetrieveTest(IsolatedStoreTest):
    def seed(self, *, task_type="debug_test_failure", fingerprint=FP, result="tests_passed"):
        conn = store.connect()
        try:
            tid = store.open_trajectory(conn, session_id="vieja", repo_fingerprint=fingerprint,
                                        task_type=task_type, base_commit="abc1234",
                                        redaction={"redactor_version": "0.1.0"})
            store.append_step(conn, tid, kind="tool_failure", tool="run_shell",
                              error_message="UnicodeDecodeError en el borde", decisive=True)
            store.close_trajectory(conn, tid, result=result)
            return tid
        finally:
            conn.close()

    def test_rankea_mismo_tipo_de_tarea_por_encima(self):
        mismo = self.seed(task_type="debug_test_failure")
        otro = self.seed(task_type="docs")
        conn = store.connect()
        try:
            scored = retrieve.candidates(conn, task_type="debug_test_failure",
                                         repo_fingerprint=FP, cfg=config.load())
            ids = [row["id"] for _, _, row in scored]
            self.assertLess(ids.index(mismo), ids.index(otro))
            self.assertIn("same_task_type", dict((r["id"], reason)
                                                 for _, reason, r in scored)[mismo])
        finally:
            conn.close()

    def test_cross_repo_apagado_por_defecto(self):
        self.seed(fingerprint="a" * 64)
        conn = store.connect()
        try:
            cfg = config.load()
            self.assertFalse(cfg["cross_repo"])
            scored = retrieve.candidates(conn, task_type="debug_test_failure",
                                         repo_fingerprint=FP, cfg=cfg)
            self.assertEqual(scored, [], "sin abstracción no se cruza de repo")
        finally:
            conn.close()

    def test_inyeccion_se_registra_y_why_la_reconstruye(self):
        """Gate de M2: toda inyección tiene que ser rastreable a su trayectoria origen."""
        source = self.seed()
        conn = store.connect()
        try:
            # La sesión nueva debe compartir fingerprint con la vieja para que aplique.
            conn.execute("UPDATE trajectories SET repo_fingerprint = ?", (FP,))
            conn.commit()
        finally:
            conn.close()

        import nightshift.context as context
        original = context.repo_fingerprint
        context.repo_fingerprint = lambda cwd: FP
        try:
            text = hook.dispatch("SessionStart", {"session_id": "nueva", "cwd": "."})
        finally:
            context.repo_fingerprint = original

        self.assertIn("nightshift", text)
        self.assertIn(source[:8], text, "el texto inyectado debe traer el id de origen")
        self.assertIn("Ninguna está verificada", text)

        conn = store.connect()
        try:
            rows = store.injections_for_session(conn, "nueva")
            self.assertEqual(len(rows), 1)
            self.assertEqual(rows[0]["source_trajectory"], source)
            back = store.injections_of_source(conn, source)
            self.assertEqual(len(back), 1)
            self.assertIsNotNone(store.get_trajectory(conn, source[:8]))
        finally:
            conn.close()

    def test_sin_historia_no_inyecta_nada(self):
        text = hook.dispatch("SessionStart", {"session_id": "limpia", "cwd": "."})
        self.assertEqual(text, "")

    def test_trayectoria_abandonada_no_se_inyecta(self):
        self.seed(result="abandoned")
        conn = store.connect()
        try:
            scored = retrieve.candidates(conn, task_type="debug_test_failure",
                                         repo_fingerprint=FP, cfg=config.load())
            self.assertEqual(scored, [], "las descartadas no se inyectan")
        finally:
            conn.close()


if __name__ == "__main__":
    unittest.main()
