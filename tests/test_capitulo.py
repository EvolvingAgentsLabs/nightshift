"""Ciclo de sueño a demanda: sellar un capítulo sin cerrar la sesión.

La sesión era la unidad de captura y la trayectoria la unidad de consolidación, así que
para soñar sobre lo que acabás de hacer había que dejar de hacerlo. `nightshift sleep`
pone el borde donde lo pone la persona que trabaja.

**El invariante que estos tests defienden es uno solo y es el que puede romper todo:** la
sesión sigue capturando después de sellar. Si dejara de hacerlo, la captura se apagaría a
mitad de sesión **en silencio** —los hooks salen 0 pase lo que pase (spec §7.2)— que es el
peor modo de falla de este proyecto y el que ya costó dos milestones.
"""

import unittest

from tests.base import IsolatedStoreTest
from nightshift import dream, hook, store

FP = "f" * 64


def _abrir(conn, session_id="viva", *, pasos=("un paso con contenido",)):
    tid = store.open_trajectory(conn, session_id=session_id, repo_fingerprint=FP,
                                task_type="debug_test_failure", base_commit="abc1234",
                                redaction={"redactor_version": "0.1.0"})
    for texto in pasos:
        store.append_step(conn, tid, kind="tool_use", tool="run_shell",
                          result_summary=texto)
    return tid


class SellarTest(IsolatedStoreTest):
    def test_la_sesion_sigue_capturando_despues_de_sellar(self):
        """El invariante. Si esto se rompe, la captura se apaga sin decir nada.

        `hook._ensure_trajectory` busca la trayectoria `open` de la sesión y, si no hay,
        abre una nueva. Sellar deja a la sesión sin trayectoria abierta exactamente hasta
        el próximo evento de hook.
        """
        conn = store.connect()
        tid = _abrir(conn, "s1")
        estado, _ = dream.seal_chapter(conn, store.get_trajectory(conn, tid))
        self.assertEqual(estado, "closed")
        self.assertIsNone(store.active_trajectory(conn, "s1"),
                          "sellado, la sesión no tiene trayectoria abierta")

        # El próximo evento de hook, sea cual sea.
        nuevo = hook._ensure_trajectory(conn, {"session_id": "s1", "cwd": "."}, {})
        conn.close()
        self.assertIsNotNone(nuevo, "la sesión dejó de capturar después de sellar")
        self.assertNotEqual(nuevo, tid, "tiene que ser una trayectoria nueva, no la sellada")

    def test_los_pasos_del_capitulo_sellado_no_se_mueven(self):
        """Sellar parte la sesión en dos; no puede además mezclarlas."""
        conn = store.connect()
        tid = _abrir(conn, "s2", pasos=("primero", "segundo"))
        dream.seal_chapter(conn, store.get_trajectory(conn, tid))
        nuevo = hook._ensure_trajectory(conn, {"session_id": "s2", "cwd": "."}, {})
        store.append_step(conn, nuevo, kind="tool_use", tool="run_shell",
                          result_summary="tercero")
        viejos = [s["result_summary"] for s in store.steps_of(conn, tid)]
        nuevos = [s["result_summary"] for s in store.steps_of(conn, nuevo)]
        conn.close()
        self.assertEqual(viejos, ["primero", "segundo"])
        self.assertEqual(nuevos, ["tercero"])

    def test_la_marca_de_capitulo_sobrevive_a_un_desenlace_con_evidencia(self):
        """El bug que encontró la primera corrida real, y el test que no lo vio.

        La primera versión guardaba `evidence or MARCA`. Con `tests_passed` —que trae su
        propia evidencia— el marcador desaparecía, justo en el caso informativo. El test
        que había cubría sólo la rama sin evidencia y pasaba en verde.
        """
        conn = store.connect()
        tid = _abrir(conn, "s8")
        # El desenlace se lee del comando guardado, no de una bandera (`_es_comando_de_test`).
        store.append_step(conn, tid, kind="tool_use", tool="run_shell",
                          args={"command": "make check"},
                          result_summary="Ran 317 tests OK")
        resultado_esperado, evidencia_propia = hook._infer_outcome(conn, tid)
        self.assertTrue(evidencia_propia, "este test no prueba nada sin evidencia propia")

        dream.seal_chapter(conn, store.get_trajectory(conn, tid))
        row = store.get_trajectory(conn, tid)
        conn.close()
        self.assertEqual(row["outcome_result"], resultado_esperado)
        self.assertIn(evidencia_propia, row["outcome_evidence"],
                      "la evidencia del desenlace no se pierde")
        self.assertIn(dream.MARCA_DE_CAPITULO, row["outcome_evidence"],
                      "y el borde puesto a mano tampoco")

    def test_el_desenlace_lo_infiere_la_misma_regla_que_session_end(self):
        """No hay una segunda heurística para lo mismo, y la evidencia dice quién selló."""
        conn = store.connect()
        tid = _abrir(conn, "s3")
        store.append_step(conn, tid, kind="tool_use", tool="run_shell",
                          result_summary="make check", decisive=True)
        esperado, _ = hook._infer_outcome(conn, tid)      # la regla de `SessionEnd`
        _, resultado = dream.seal_chapter(conn, store.get_trajectory(conn, tid))
        row = store.get_trajectory(conn, tid)
        conn.close()
        self.assertEqual(resultado, esperado)
        self.assertEqual(row["outcome_result"], esperado)
        self.assertIn(dream.MARCA_DE_CAPITULO, row["outcome_evidence"] or "",
                      "el store tiene que poder distinguir un borde puesto a mano")

    def test_un_capitulo_de_otro_repo_no_aparece(self):
        conn = store.connect()
        _abrir(conn, "s4")
        otro = store.open_trajectory(conn, session_id="s5", repo_fingerprint="a" * 64,
                                     task_type="general", base_commit="abc1234",
                                     redaction={"redactor_version": "0.1.0"})
        store.append_step(conn, otro, kind="tool_use", tool="run_shell", result_summary="x")
        ids = [r["id"] for r in dream.open_chapters(conn, FP)]
        conn.close()
        self.assertNotIn(otro, ids)

    def test_open_chapters_ordena_por_actividad_no_por_apertura(self):
        """Una sesión vieja que sigue trabajando es más "en curso" que una nueva parada.

        Los timestamps se fijan a mano: `store.now()` tiene resolución de segundo y en un
        test todo pasa en el mismo. Es el mismo criterio que `stale_open_trajectories`
        —última actividad, nunca antigüedad— y por el mismo motivo (spec §5.8).
        """
        conn = store.connect()
        vieja = _abrir(conn, "s6", pasos=("trabajo viejo",))
        nueva = _abrir(conn, "s7", pasos=("abierta después y quieta",))
        conn.execute("UPDATE trajectories SET created_at = ? WHERE id = ?",
                     ("2026-08-01T00:00:00Z", vieja))
        conn.execute("UPDATE trajectories SET created_at = ? WHERE id = ?",
                     ("2026-08-02T00:00:00Z", nueva))
        conn.execute("UPDATE steps SET at = ? WHERE trajectory_id = ?",
                     ("2026-08-02T00:00:00Z", nueva))
        conn.execute("UPDATE steps SET at = ? WHERE trajectory_id = ?",
                     ("2026-08-03T00:00:00Z", vieja))      # sigue trabajando
        conn.commit()
        ids = [r["id"] for r in dream.open_chapters(conn, FP)]
        conn.close()
        self.assertEqual(ids[0], vieja, "la de actividad más reciente va primera")
        self.assertEqual(ids[1], nueva)


class AcotarLaCorridaTest(IsolatedStoreTest):
    """`sleep` consolida el grupo del capítulo, no la semana entera."""

    class _Modelo:
        name = "fake"

        def __init__(self):
            self.prompts = []

        def ask_json(self, prompt):
            self.prompts.append(prompt)
            return {"pattern": "Una etapa valida la forma del registro y nunca su "
                               "contenido, asi que lo vacio pasa como valido."}

    def _cerrada(self, conn, session_id, *, task_type, texto):
        tid = _abrir(conn, session_id, pasos=(texto,))
        conn.execute("UPDATE trajectories SET task_type = ? WHERE id = ?",
                     (task_type, tid))
        store.close_trajectory(conn, tid, result="tests_passed")
        return tid

    def test_only_trajectory_deja_afuera_los_otros_grupos(self):
        conn = store.connect()
        mio = self._cerrada(conn, "a", task_type="debug_test_failure",
                            texto="el decodificador explota en el primer byte")
        self._cerrada(conn, "b", task_type="implement_feature",
                      texto="se agrego el comando nuevo al parser")
        from nightshift import config

        modelo = self._Modelo()
        reporte = dream.consolidate(conn, modelo, cfg=config.load(), lookback_days=3650,
                                    only_trajectory=mio)
        conn.close()
        self.assertEqual(reporte["groups"], 1, "consolidó más de un grupo")
        self.assertEqual(reporte["only_trajectory"], mio)
        self.assertEqual([c["trajectory"] for c in reporte["candidates"]], [mio])
        self.assertEqual(len(modelo.prompts), 1,
                         "una llamada al modelo por grupo: acotar tiene que ahorrar")

    def test_sin_acotar_consolida_todos(self):
        """El control: si `only_trajectory` no filtrara nada, el test de arriba pasaría igual."""
        conn = store.connect()
        self._cerrada(conn, "a", task_type="debug_test_failure",
                      texto="el decodificador explota en el primer byte")
        self._cerrada(conn, "b", task_type="implement_feature",
                      texto="se agrego el comando nuevo al parser")
        from nightshift import config

        reporte = dream.consolidate(conn, self._Modelo(), cfg=config.load(),
                                    lookback_days=3650)
        conn.close()
        self.assertEqual(reporte["groups"], 2)


if __name__ == "__main__":
    unittest.main()
