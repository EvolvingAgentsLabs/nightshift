"""Trayectorias huérfanas: las que quedaron `open` porque la sesión murió (T3).

Una huérfana no es sólo un registro sucio: el retrieval mira `closed`, `candidate` y
`procedure`, así que una trayectoria `open` para siempre es una trayectoria que **nunca**
va a ser recuperable. Se pierde entera.

El corte es por falta de actividad, no por antigüedad, y por eso hay un test de que una
sesión larga pero viva sobrevive: dos sesiones simultáneas son normales y cerrarle la
trayectoria a la que sigue trabajando la partiría en dos.
"""

import json
import unittest

from tests.base import IsolatedStoreTest
from nightshift import config, hook, retrieve, store

FP = "f" * 64


class OrphanTest(IsolatedStoreTest):
    def seed_open(self, *, session_id, hours_ago, steps=1, task_type="debug_test_failure"):
        """Una trayectoria `open` cuyo último paso ocurrió hace `hours_ago` horas."""
        stamp = store.hours_ago(hours_ago)
        conn = store.connect()
        try:
            tid = store.open_trajectory(conn, session_id=session_id, repo_fingerprint=FP,
                                        task_type=task_type,
                                        redaction={"redactor_version": "0.1.0"})
            for _ in range(steps):
                store.append_step(conn, tid, kind="tool_failure", tool="run_shell",
                                  error_message="UnicodeDecodeError", decisive=True)
            conn.execute("UPDATE trajectories SET created_at = ? WHERE id = ?", (stamp, tid))
            conn.execute("UPDATE steps SET at = ? WHERE trajectory_id = ?", (stamp, tid))
            conn.commit()
            return tid
        finally:
            conn.close()

    def status_of(self, tid):
        conn = store.connect()
        try:
            return store.get_trajectory(conn, tid)["status"]
        finally:
            conn.close()

    def start_session(self, session_id="viva"):
        return hook.dispatch("SessionStart", {"session_id": session_id, "cwd": "."})

    # ---------------------------------------------------------------- el gate de T3
    def test_cierra_la_huerfana_y_no_toca_la_sesion_en_curso(self):
        huerfana = self.seed_open(session_id="muerta", hours_ago=48)
        self.start_session("viva")

        self.assertEqual(self.status_of(huerfana), "closed")
        conn = store.connect()
        try:
            row = store.active_trajectory(conn, "viva")
            self.assertIsNotNone(row, "la trayectoria de la sesión en curso sigue abierta")
            self.assertEqual(row["status"], "open")
            cerrada = store.get_trajectory(conn, huerfana)
            self.assertIsNotNone(cerrada["closed_at"])
            self.assertEqual(cerrada["outcome_result"], "unknown")
            self.assertIn("huérfana", cerrada["outcome_evidence"])
        finally:
            conn.close()

    def test_una_sesion_reciente_de_otra_terminal_no_se_toca(self):
        """Dos sesiones simultáneas son normales. El corte es por inactividad."""
        vecina = self.seed_open(session_id="otra-terminal", hours_ago=1)
        self.start_session("viva")
        self.assertEqual(self.status_of(vecina), "open")

    def test_una_sesion_larga_pero_activa_sobrevive(self):
        """Abierta hace tres días, con un paso de hace diez minutos: está viva."""
        larga = self.seed_open(session_id="maraton", hours_ago=72)
        conn = store.connect()
        try:
            conn.execute("UPDATE steps SET at = ? WHERE trajectory_id = ?",
                         (store.hours_ago(0.16), larga))
            conn.commit()
        finally:
            conn.close()
        self.start_session("viva")
        self.assertEqual(self.status_of(larga), "open",
                         "el corte mira el último paso, no la fecha de apertura")

    def test_la_huerfana_sin_pasos_se_descarta(self):
        vacia = self.seed_open(session_id="muerta-vacia", hours_ago=48, steps=0)
        self.start_session("viva")
        self.assertEqual(self.status_of(vacia), "discarded",
                         "sin pasos no hay señal utilizable")

    def test_cerrarla_la_vuelve_recuperable(self):
        """El motivo de existir de T3: `open` para siempre es material perdido."""
        huerfana = self.seed_open(session_id="muerta", hours_ago=48)
        conn = store.connect()
        try:
            scored = retrieve.candidates(conn, task_type="debug_test_failure",
                                         repo_fingerprint=FP, cfg=config.load())
            self.assertEqual(scored, [], "mientras está `open` el retrieval no la ve")
        finally:
            conn.close()

        self.start_session("viva")

        conn = store.connect()
        try:
            scored = retrieve.candidates(conn, task_type="debug_test_failure",
                                         repo_fingerprint=FP, cfg=config.load())
            self.assertIn(huerfana, [row["id"] for _, _, row in scored])
        finally:
            conn.close()

    def test_el_umbral_es_configurable_y_apagable(self):
        huerfana = self.seed_open(session_id="muerta", hours_ago=48)
        path = config.config_path()
        cfg = json.loads(path.read_text(encoding="utf-8"))
        cfg["orphan_after_hours"] = 0
        path.write_text(json.dumps(cfg), encoding="utf-8")

        self.start_session("viva")
        self.assertEqual(self.status_of(huerfana), "open", "en 0 el barrido no corre")

        cfg["orphan_after_hours"] = 24
        path.write_text(json.dumps(cfg), encoding="utf-8")
        self.start_session("viva2")
        self.assertEqual(self.status_of(huerfana), "closed")

    def test_el_default_esta_declarado(self):
        self.assertEqual(config.DEFAULTS["orphan_after_hours"], 12)
        self.assertEqual(config.load()["orphan_after_hours"], 12)

    def test_lo_dice_en_pantalla(self):
        self.seed_open(session_id="muerta", hours_ago=48)
        _, message = self.start_session("viva")
        self.assertIn("huérfana", message)


if __name__ == "__main__":
    unittest.main()
