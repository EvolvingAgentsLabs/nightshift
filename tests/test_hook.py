"""Los hooks capturan lo correcto y, sobre todo, nunca rompen la sesión."""

import json
import unittest
from pathlib import Path

from tests.base import IsolatedStoreTest
from nightshift import config, hook, store


def payload(**kwargs):
    base = {"session_id": "sess", "cwd": "."}
    base.update(kwargs)
    return base


# Payloads con la forma REAL de Claude Code, sondeada el 2026-08-26 ejecutando los hooks
# de verdad. Las claves están acá arriba, sueltas, para que se vean: leer las equivocadas
# no rompe nada, no loguea nada y no falla ningún test estructural — simplemente captura
# vacío para siempre.
CLAVES_REALES = {
    "SessionStart": ["cwd", "hook_event_name", "session_id", "source", "transcript_path"],
    "UserPromptSubmit": ["cwd", "hook_event_name", "permission_mode", "prompt", "prompt_id",
                         "session_id", "transcript_path"],
    "PostToolUse": ["cwd", "duration_ms", "effort", "hook_event_name", "permission_mode",
                    "prompt_id", "session_id", "tool_input", "tool_name", "tool_response",
                    "tool_use_id", "transcript_path"],
    "PostToolUseFailure": ["cwd", "duration_ms", "effort", "error", "hook_event_name",
                           "is_interrupt", "permission_mode", "prompt_id", "session_id",
                           "tool_input", "tool_name", "tool_use_id", "transcript_path"],
    "Stop": ["cwd", "hook_event_name", "last_assistant_message", "permission_mode",
             "prompt_id", "session_id", "stop_hook_active", "transcript_path"],
    "SessionEnd": ["cwd", "hook_event_name", "prompt_id", "reason", "session_id",
                   "transcript_path"],
}


class PayloadRealTest(IsolatedStoreTest):
    """El bug más caro de M1+M2: leer los nombres de campo equivocados.

    `prompt` se leía como `user_input`, `tool_response` como `tool_output` y `error` como
    `error_message`. Consecuencia: el tipo de tarea nunca se clasificó, ninguna corrección
    se detectó, y **todos los pasos quedaron sin contenido** — durante dos milestones, en
    silencio, porque los hooks salen 0 pase lo que pase (spec §7.2) y el selftest usaba
    los mismos nombres inventados que el código.
    """

    def sesion_real(self):
        base = {"session_id": "real", "cwd": ".", "transcript_path": "/tmp/t.jsonl"}
        hook.dispatch("SessionStart", dict(base, source="startup"))
        hook.dispatch("UserPromptSubmit", dict(base, prompt="los tests fallan con "
                                                            "UnicodeDecodeError"))
        hook.dispatch("PostToolUse", dict(
            base, tool_name="Read", tool_use_id="t1", duration_ms=12,
            tool_input={"file_path": "parser.py"},
            tool_response={"type": "text", "file": {"content": "def parse(): ..."}}))
        hook.dispatch("PostToolUseFailure", dict(
            base, tool_name="Bash", tool_use_id="t2", is_interrupt=False,
            tool_input={"command": "pytest -q"},
            error="UnicodeDecodeError: 'utf-8' codec can't decode byte"))
        hook.dispatch("Stop", dict(base, last_assistant_message="listo"))
        hook.dispatch("SessionEnd", dict(base, reason="clear"))
        conn = store.connect()
        try:
            row = conn.execute("SELECT * FROM trajectories").fetchone()
            return dict(row), [dict(s) for s in store.steps_of(conn, row["id"])]
        finally:
            conn.close()

    def test_el_prompt_clasifica_el_tipo_de_tarea(self):
        row, _ = self.sesion_real()
        self.assertEqual(row["task_type"], "debug_test_failure",
                         "el prompt llega en `prompt`, no en `user_input`")

    def test_la_salida_de_la_tool_se_captura(self):
        _, pasos = self.sesion_real()
        uso = [p for p in pasos if p["kind"] == "tool_use"][0]
        self.assertTrue(uso["result_summary"], "la salida llega en `tool_response`")
        self.assertIn("def parse", uso["result_summary"])

    def test_el_error_de_la_tool_se_captura(self):
        _, pasos = self.sesion_real()
        fallo = [p for p in pasos if p["kind"] == "tool_failure"][0]
        self.assertTrue(fallo["error_message"], "el error llega en `error`")
        self.assertIn("UnicodeDecodeError", fallo["error_message"])
        self.assertTrue(fallo["decisive"])

    def test_ningun_paso_de_tool_queda_vacio(self):
        """La aserción que faltaba: estructura correcta y contenido vacío es el bug."""
        _, pasos = self.sesion_real()
        for paso in pasos:
            if paso["kind"] in ("tool_use", "tool_failure"):
                with self.subTest(idx=paso["idx"]):
                    self.assertTrue(paso["result_summary"] or paso["error_message"])

    def test_una_correccion_del_usuario_se_detecta(self):
        base = {"session_id": "corr", "cwd": "."}
        hook.dispatch("SessionStart", dict(base))
        hook.dispatch("PostToolUse", dict(base, tool_name="Edit",
                                          tool_input={"file_path": "a.py"},
                                          tool_response={"type": "text", "file": "ok"}))
        hook.dispatch("UserPromptSubmit", dict(base, prompt="no, eso está mal"))
        conn = store.connect()
        try:
            tid = store.active_trajectory(conn, "corr")["id"]
            self.assertTrue(store.steps_of(conn, tid)[-1]["contradicted"])
        finally:
            conn.close()

    def test_una_interrupcion_no_es_senal_decisiva(self):
        """`is_interrupt` es alguien apretando Esc, no una herramienta que falló."""
        base = {"session_id": "esc", "cwd": "."}
        hook.dispatch("SessionStart", dict(base))
        hook.dispatch("PostToolUseFailure", dict(base, tool_name="Bash", is_interrupt=True,
                                                 tool_input={"command": "sleep 900"},
                                                 error="interrupted by user"))
        conn = store.connect()
        try:
            tid = store.active_trajectory(conn, "esc")["id"]
            paso = store.steps_of(conn, tid)[-1]
            self.assertEqual(paso["kind"], "tool_failure")
            self.assertFalse(paso["decisive"])
        finally:
            conn.close()

    def test_los_nombres_de_campo_estan_documentados(self):
        """Si el harness los cambia otra vez, esto dice contra qué se verificó y cuándo."""
        spec = (Path(__file__).resolve().parent.parent / "doc" / "00-spec.md").read_text(
            encoding="utf-8")
        for evento, claves in CLAVES_REALES.items():
            with self.subTest(evento=evento):
                self.assertIn(evento, spec)
        for clave in ("prompt", "tool_response", "error", "is_interrupt"):
            with self.subTest(clave=clave):
                self.assertIn("`%s`" % clave, spec)


class HookTest(IsolatedStoreTest):
    def test_sin_config_no_captura(self):
        config.config_path().unlink()
        self.assertFalse(config.is_enabled())
        text, message = hook.dispatch("SessionStart", payload())
        self.assertIn("no configurado", text)
        self.assertIn("nightshift init", message)
        hook.dispatch("PostToolUse", payload(tool_name="Bash", tool_input={"command": "ls"}))
        self.assertFalse(config.db_path().exists())

    def test_post_tool_use_failure_crea_tool_failure(self):
        hook.dispatch("SessionStart", payload())
        hook.dispatch("PostToolUseFailure", payload(
            tool_name="Bash", tool_use_id="t1", tool_input={"command": "pytest"},
            error_message="AssertionError: nope"))
        conn = store.connect()
        try:
            tid = store.active_trajectory(conn, "sess")["id"]
            steps = store.steps_of(conn, tid)
            self.assertEqual(steps[-1]["kind"], "tool_failure")
            self.assertTrue(steps[-1]["decisive"], "un fallo de tool es señal decisiva")
            self.assertIn("AssertionError", steps[-1]["error_message"])
        finally:
            conn.close()

    def test_stop_no_cierra_la_trayectoria(self):
        """Stop dispara por turno, no por sesión. Cerrar ahí la partiría (spec §5.6)."""
        hook.dispatch("SessionStart", payload())
        hook.dispatch("Stop", payload(last_assistant_message="listo"))
        conn = store.connect()
        try:
            self.assertIsNotNone(store.active_trajectory(conn, "sess"),
                                 "Stop no debe cerrar la trayectoria")
        finally:
            conn.close()

    def test_session_end_cierra(self):
        hook.dispatch("SessionStart", payload())
        hook.dispatch("PostToolUse", payload(tool_name="Read", tool_input={"file_path": "a.py"},
                                             tool_output="x"))
        hook.dispatch("SessionEnd", payload())
        conn = store.connect()
        try:
            self.assertIsNone(store.active_trajectory(conn, "sess"))
            row = conn.execute("SELECT * FROM trajectories").fetchone()
            self.assertEqual(row["status"], "closed")
        finally:
            conn.close()

    def test_correccion_marca_contradicho(self):
        hook.dispatch("SessionStart", payload())
        hook.dispatch("PostToolUse", payload(tool_name="Edit", tool_input={"file_path": "a.py"},
                                             tool_output="ok"))
        hook.dispatch("UserPromptSubmit", payload(user_input="no, eso está mal"))  # alias viejo
        conn = store.connect()
        try:
            tid = store.active_trajectory(conn, "sess")["id"]
            self.assertTrue(store.steps_of(conn, tid)[-1]["contradicted"])
        finally:
            conn.close()

    def test_el_prompt_no_se_persiste(self):
        """UserPromptSubmit sólo aporta la etiqueta de clasificación, no el texto."""
        secreto = "la clave de produccion es zanahoria-violeta-42"
        hook.dispatch("SessionStart", payload())
        hook.dispatch("UserPromptSubmit", payload(user_input="los tests fallan. " + secreto))
        blob = config.db_path().read_bytes()
        self.assertNotIn(b"zanahoria-violeta-42", blob)
        conn = store.connect()
        try:
            row = store.active_trajectory(conn, "sess")
            self.assertEqual(row["task_type"], "debug_test_failure")
        finally:
            conn.close()

    def test_precompact_sella(self):
        hook.dispatch("SessionStart", payload())
        hook.dispatch("PreCompact", payload(compaction_reason="auto"))
        conn = store.connect()
        try:
            tid = store.active_trajectory(conn, "sess")["id"]
            self.assertEqual(store.steps_of(conn, tid)[-1]["kind"], "compact_snapshot")
        finally:
            conn.close()

    def test_deny_path_no_entra_al_store(self):
        hook.dispatch("SessionStart", payload())
        hook.dispatch("PostToolUse", payload(
            tool_name="Read", tool_use_id="t9",
            tool_input={"file_path": "/home/x/proj/.env"},
            tool_output="API_TOKEN=tok_live_nunca_deberia_estar"))
        blob = config.db_path().read_bytes()
        self.assertNotIn(b"tok_live_nunca_deberia_estar", blob)
        self.assertNotIn(b"/home/x/proj/.env", blob)

    def test_nunca_levanta_con_payload_basura(self):
        for event in hook.EVENTS:
            for bad in ({}, {"session_id": None}, {"session_id": "s", "tool_input": "no-es-dict"},
                        {"session_id": "s", "cwd": "/no/existe/nunca"}):
                with self.subTest(event=event, bad=bad):
                    try:
                        hook.dispatch(event, dict(bad))
                    except Exception as exc:  # pragma: no cover
                        self.fail("%s levantó con %r: %s" % (event, bad, exc))

    def test_main_siempre_sale_cero(self):
        import io
        import sys
        saved_in, saved_out = sys.stdin, sys.stdout
        try:
            sys.stdin = io.StringIO("no es json valido {{{")
            sys.stdout = io.StringIO()
            self.assertEqual(hook.main(["SessionStart"]), 0)
            sys.stdin = io.StringIO(json.dumps(payload()))
            sys.stdout = io.StringIO()
            self.assertEqual(hook.main(["EventoInventado"]), 0)
        finally:
            sys.stdin, sys.stdout = saved_in, saved_out


if __name__ == "__main__":
    unittest.main()


class DenyPathStepTest(IsolatedStoreTest):
    """Regresión: un tool call que toca un deny_path no deja rastro.

    La primera versión sólo borraba el path y seguía guardando el **contenido** leído.
    La spec §8.1 no admite ni el path, ni el contenido, ni el hecho de que existe.
    """

    def test_el_paso_entero_desaparece(self):
        hook.dispatch("SessionStart", payload())
        hook.dispatch("PostToolUse", payload(
            tool_name="Read", tool_use_id="x",
            tool_input={"file_path": "/repo/.env"},
            tool_output="SECRETO=jamas-deberia-persistir"))
        conn = store.connect()
        try:
            tid = store.active_trajectory(conn, "sess")["id"]
            self.assertEqual(store.steps_of(conn, tid), [],
                             "no debe quedar ningún paso")
            import json as _json
            redaction = _json.loads(store.get_trajectory(conn, tid)["redaction_json"])
            self.assertEqual(redaction["deny_path_hits"], 1, "pero sí debe contarse")
            self.assertEqual(redaction["redactor_version"], "0.1.0")
        finally:
            conn.close()
        blob = config.db_path().read_bytes()
        self.assertNotIn(b"jamas-deberia-persistir", blob)
        self.assertNotIn(b"/repo/.env", blob)

    def test_un_tool_call_normal_si_se_captura(self):
        hook.dispatch("SessionStart", payload())
        hook.dispatch("PostToolUse", payload(
            tool_name="Read", tool_use_id="y",
            tool_input={"file_path": "/repo/src/main.py"}, tool_output="def main(): ..."))
        conn = store.connect()
        try:
            tid = store.active_trajectory(conn, "sess")["id"]
            self.assertEqual(len(store.steps_of(conn, tid)), 1)
        finally:
            conn.close()


class EmitShapeTest(IsolatedStoreTest):
    """`additionalContext` va al contexto del modelo; `systemMessage` a la pantalla.

    Sin la segunda, un plugin que funciona y uno que no hace nada se ven idénticos
    desde la terminal: fue exactamente la confusión que motivó este test.
    """

    def run_main(self, event, data):
        import io
        import sys
        saved_in, saved_out = sys.stdin, sys.stdout
        try:
            sys.stdin = io.StringIO(json.dumps(data))
            sys.stdout = io.StringIO()
            self.assertEqual(hook.main([event]), 0)
            raw = sys.stdout.getvalue()
        finally:
            sys.stdin, sys.stdout = saved_in, saved_out
        return json.loads(raw)["hookSpecificOutput"] if raw.strip() else {}

    def test_session_start_siempre_dice_algo_al_usuario(self):
        out = self.run_main("SessionStart", payload())
        self.assertEqual(out["hookEventName"], "SessionStart")
        self.assertIn("nightshift", out["systemMessage"])
        self.assertIn("sin memoria previa", out["systemMessage"])

    def test_sin_config_el_usuario_se_entera(self):
        config.config_path().unlink()
        out = self.run_main("SessionStart", payload())
        self.assertIn("NO configurado", out["systemMessage"])
        self.assertIn("no configurado", out["additionalContext"])

    def test_los_hooks_de_captura_no_le_hablan_al_usuario(self):
        """Un mensaje por tool call sería ruido insoportable."""
        self.run_main("SessionStart", payload())
        for event, extra in (("PostToolUse", {"tool_name": "Read",
                                              "tool_input": {"file_path": "a.py"},
                                              "tool_output": "x"}),
                             ("PreCompact", {"compaction_reason": "auto"}),
                             ("Stop", {}), ("SessionEnd", {})):
            with self.subTest(event=event):
                out = self.run_main(event, payload(**extra))
                self.assertNotIn("systemMessage", out)
