"""Retrieval e inyección (M2), y el gate de M2: `why` reconstruye el origen."""

import unittest

from tests.base import IsolatedStoreTest
from nightshift import config, hook, retrieve, store

FP = "f" * 64


class RetrieveTest(IsolatedStoreTest):
    def seed(self, *, task_type="debug_test_failure", fingerprint=FP, result="tests_passed",
             decisive=True):
        conn = store.connect()
        try:
            tid = store.open_trajectory(conn, session_id="vieja", repo_fingerprint=fingerprint,
                                        task_type=task_type, base_commit="abc1234",
                                        redaction={"redactor_version": "0.1.0"})
            store.append_step(conn, tid, kind="tool_failure", tool="run_shell",
                              error_message="UnicodeDecodeError en el borde", decisive=decisive)
            store.close_trajectory(conn, tid, result=result)
            return tid
        finally:
            conn.close()

    def fixed_fingerprint(self):
        """Fija el fingerprint del repo para que la sesión de test matchee lo sembrado."""
        import nightshift.context as context
        original = context.repo_fingerprint
        context.repo_fingerprint = lambda cwd: FP

        class _Restore:
            def __enter__(self_inner):
                return self_inner

            def __exit__(self_inner, *exc):
                context.repo_fingerprint = original
                return False

        return _Restore()

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
            text, message = hook.dispatch("SessionStart",
                                          {"session_id": "nueva", "cwd": "."})
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

    def test_general_no_cuenta_como_mismo_tipo_de_tarea(self):
        """`general` es "sin clasificar", no un tipo. Contarlo mentía en el `why`."""
        self.seed(task_type="general")
        conn = store.connect()
        try:
            scored = retrieve.candidates(conn, task_type="general", repo_fingerprint=FP,
                                         cfg=config.load())
            self.assertTrue(scored, "sigue siendo candidata por repo y recencia")
            self.assertNotIn("same_task_type", scored[0][1])
        finally:
            conn.close()

    def test_retrieval_por_tipo_de_tarea_en_el_primer_prompt(self):
        """Gate de T2: `SessionStart` no puede rankear por tipo, el primer prompt sí.

        Se siembran tres trayectorias de otro tipo que llenan el cupo de `SessionStart`
        (que sólo puede rankear por repo y recencia) y una de debugging que se queda
        afuera. Cuando el prompt clasifica la tarea, la de debugging entra — y ninguna
        se inyecta dos veces.
        """
        for _ in range(3):
            self.seed(task_type="docs", result="tests_passed")
        debug = self.seed(task_type="debug_test_failure", result="unknown", decisive=False)

        with self.fixed_fingerprint():
            primero, _ = hook.dispatch("SessionStart", {"session_id": "s", "cwd": "."})
            self.assertNotIn(debug[:8], primero, "sin tipo de tarea no puede elegirla")
            self.assertNotIn("same_task_type", primero)

            segundo, mensaje = hook.dispatch("UserPromptSubmit", {
                "session_id": "s", "cwd": ".",
                "user_input": "los tests fallan con UnicodeDecodeError"})

        self.assertIn(debug[:8], segundo, "el prompt clasificó la tarea: ahora sí aplica")
        self.assertIn("debug_test_failure", mensaje)

        conn = store.connect()
        try:
            rows = store.injections_for_session(conn, "s")
            segunda = [r for r in rows if r["source_trajectory"] == debug]
            self.assertEqual(len(segunda), 1)
            self.assertIn("same_task_type", segunda[0]["reason"])
            fuentes = [r["source_trajectory"] for r in rows]
            self.assertEqual(len(fuentes), len(set(fuentes)),
                             "ninguna trayectoria se inyecta dos veces en la misma sesión")
            self.assertEqual(store.active_trajectory(conn, "s")["task_type"],
                             "debug_test_failure")
        finally:
            conn.close()

    def test_no_se_reinyecta_lo_que_ya_se_dijo(self):
        source = self.seed(task_type="debug_test_failure")
        with self.fixed_fingerprint():
            primero, _ = hook.dispatch("SessionStart", {"session_id": "s2", "cwd": "."})
            self.assertIn(source[:8], primero)
            segundo = hook.dispatch("UserPromptSubmit", {
                "session_id": "s2", "cwd": ".",
                "user_input": "los tests fallan con UnicodeDecodeError"})[0]
        self.assertEqual(segundo, "", "ya se había inyectado en SessionStart")
        conn = store.connect()
        try:
            self.assertEqual(len(store.injections_for_session(conn, "s2")), 1)
        finally:
            conn.close()

    def test_solo_inyecta_una_vez_por_sesion_aunque_haya_mas_prompts(self):
        self.seed(task_type="docs")
        debug = self.seed(task_type="debug_test_failure")
        with self.fixed_fingerprint():
            hook.dispatch("SessionStart", {"session_id": "s3", "cwd": "."})
            hook.dispatch("UserPromptSubmit", {"session_id": "s3", "cwd": ".",
                                               "user_input": "los tests fallan"})
            tercero = hook.dispatch("UserPromptSubmit", {
                "session_id": "s3", "cwd": ".",
                "user_input": "y ahora este otro test también falla"})[0]
        self.assertEqual(tercero, "", "el tipo de tarea ya dejó de ser general una vez")
        conn = store.connect()
        try:
            rows = store.injections_for_session(conn, "s3")
            fuentes = [r["source_trajectory"] for r in rows]
            self.assertEqual(len(fuentes), len(set(fuentes)))
            self.assertIn(debug, fuentes)
        finally:
            conn.close()

    def test_sin_historia_no_inyecta_nada(self):
        text, message = hook.dispatch("SessionStart",
                                      {"session_id": "limpia", "cwd": "."})
        self.assertEqual(text, "")
        self.assertIn("sin memoria previa", message)

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
