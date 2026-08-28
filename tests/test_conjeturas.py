"""Resolver conjeturas: el bucle que las proyecciones abren (plan §7, F1).

Dream proyecta síntomas que nadie observó. Hasta acá no había forma de decirle al store
que uno pasó, o que no puede pasar: la conjetura quedaba abierta para siempre y seguía
enganchando igual. **Una conjetura que nadie resuelve no es memoria, es una nota.**

Lo que estos tests defienden es la frontera, que ahora tiene tres lados y no dos:

- una **refutada** no vuelve a engancharse — alguien sabe por qué no puede pasar;
- una **confirmada** sigue pesando la mitad — que el mecanismo haya acertado no vuelve a
  este trabajo el que lo observó, y borrar esa distinción borra ADR-004 entero;
- una resolución **sin evidencia y sin autor no es una resolución**, ni del modelo ni de
  una persona.
"""

import unittest

from tests.base import IsolatedStoreTest
from nightshift import audit, config, redact, retrieve, store

FP = "f" * 64
PROYECCIONES = ["los totales de un reporte no cierran porque un registro aparece duplicado",
                "un indice devuelve vacio en lugar de fallar"]


def _candidata(conn, *, proyectadas=PROYECCIONES, session="s"):
    tid = store.open_trajectory(conn, session_id=session, repo_fingerprint=FP,
                                task_type="debug_test_failure", base_commit="abc1234",
                                redaction={"redactor_version": "0.1.0"})
    store.append_step(conn, tid, kind="tool_failure", tool="run_shell",
                      error_message="KeyError en el borde", decisive=True)
    store.close_trajectory(conn, tid, result="tests_passed")
    store.promote_to_candidate(
        conn, tid,
        abstraction={"pattern": "El indice se arma normalizando la clave pero la consulta "
                                "busca con la clave cruda.",
                     "signals": ["una clave que esta en el indice levanta KeyError"]},
        valid_when=[], hypothesis=None, weight=0.6, projected_signals=proyectadas)
    return tid


class SincronizacionTest(IsolatedStoreTest):
    def test_promover_deja_las_conjeturas_con_estado(self):
        """Sincronizar desde otro lado dejaría una ventana con proyección y sin estado."""
        conn = store.connect()
        tid = _candidata(conn)
        filas = store.projections_of(conn, tid)
        conn.close()
        self.assertEqual([f["text"] for f in filas], PROYECCIONES)
        self.assertEqual({f["status"] for f in filas}, {"open"})

    def test_sincronizar_dos_veces_no_duplica_ni_pisa_un_veredicto(self):
        """Es lo único que `sync` no puede hacer: reabrir algo que alguien resolvió."""
        conn = store.connect()
        tid = _candidata(conn)
        primera = store.projections_of(conn, tid)[0]
        store.resolve_projection(conn, primera["id"], status="refuted",
                                 evidence="no puede pasar porque el indice se recalcula",
                                 resolved_by="alguien")
        self.assertEqual(store.sync_projections(conn), 0)
        filas = store.projections_of(conn, tid)
        conn.close()
        self.assertEqual(len(filas), 2, "se duplicaron")
        self.assertEqual(filas[0]["status"], "refuted", "el veredicto se pisó")

    def test_el_json_original_no_se_toca(self):
        """`projected_signals_json` lo define `trajectory.v1`: es el dato, no el estado."""
        conn = store.connect()
        tid = _candidata(conn)
        store.resolve_projection(conn, store.projections_of(conn, tid)[0]["id"],
                                 status="refuted", evidence="porque sí que no",
                                 resolved_by="alguien")
        row = store.get_trajectory(conn, tid)
        conn.close()
        self.assertIn(PROYECCIONES[0], row["projected_signals_json"])


class VeredictoTest(IsolatedStoreTest):
    def _una(self, conn):
        return store.projections_of(conn, _candidata(conn))[0]["id"]

    def test_resolver_sin_evidencia_no_resuelve(self):
        """Refutar sin motivo es olvidar con otro nombre."""
        conn = store.connect()
        pid = self._una(conn)
        for evidencia in ("", "   ", None):
            with self.assertRaises(ValueError):
                store.resolve_projection(conn, pid, status="refuted", evidence=evidencia,
                                         resolved_by="alguien")
        conn.close()

    def test_resolver_sin_autor_no_resuelve(self):
        """Un veredicto sin autor no se puede revisar."""
        conn = store.connect()
        pid = self._una(conn)
        with self.assertRaises(ValueError):
            store.resolve_projection(conn, pid, status="confirmed", evidence="la vi",
                                     resolved_by="")
        conn.close()

    def test_no_hay_un_estado_tibio(self):
        """El valor de esto es que obliga a decidir."""
        conn = store.connect()
        pid = self._una(conn)
        for estado in ("open", "probablemente", "maybe"):
            with self.assertRaises(ValueError):
                store.resolve_projection(conn, pid, status=estado, evidence="e",
                                         resolved_by="a")
        conn.close()

    def test_sin_resolver_ninguna_el_acierto_es_None_y_no_cero(self):
        """"Nadie miró" no es "ninguna acertó", y confundirlos es el verde vacuo."""
        conn = store.connect()
        _candidata(conn)
        stats = store.projection_stats(conn)
        conn.close()
        self.assertIsNone(stats["hit_rate"])
        self.assertEqual(stats["open"], 2)

    def test_el_acierto_se_calcula_sobre_las_resueltas(self):
        conn = store.connect()
        filas = store.projections_of(conn, _candidata(conn))
        store.resolve_projection(conn, filas[0]["id"], status="confirmed",
                                 evidence="la vi", resolved_by="a")
        store.resolve_projection(conn, filas[1]["id"], status="refuted",
                                 evidence="no puede", resolved_by="a")
        stats = store.projection_stats(conn)
        conn.close()
        self.assertEqual(stats["hit_rate"], 0.5)
        self.assertEqual(stats["resolved"], 2)


class EngancheTest(IsolatedStoreTest):
    """La frontera de tres lados, medida en el ranking."""

    PROMPT = "los totales del reporte no cierran y un cliente aparece duplicado"

    def _rank(self, conn, tid):
        """El puntaje de **esa** trayectoria. Sembrar dos candidatas y mirar `scored[0]`
        compara dos filas distintas, no la misma antes y después."""
        for score, motivos, row in retrieve.candidates(
                conn, task_type="debug_test_failure", repo_fingerprint=FP,
                cfg=config.load(), prompt=self.PROMPT):
            if row["id"] == tid:
                return score, motivos
        return 0.0, ""

    def _antes_y_despues(self, estado):
        """La misma trayectoria, antes y después de resolver su primera conjetura."""
        conn = store.connect()
        tid = _candidata(conn)
        antes = self._rank(conn, tid)
        store.resolve_projection(conn, store.projections_of(conn, tid)[0]["id"],
                                 status=estado, evidence="motivo suficiente",
                                 resolved_by="alguien")
        despues = self._rank(conn, tid)
        conn.close()
        return antes, despues

    def test_una_refutada_deja_de_enganchar(self):
        """Alguien fue a mirar y sabe por qué no puede pasar."""
        (antes, motivos_antes), (despues, motivos_despues) = self._antes_y_despues("refuted")
        self.assertIn("projected_match", motivos_antes)
        self.assertNotIn("projected_match", motivos_despues)
        self.assertLess(despues, antes)

    def test_confirmarla_ni_la_apaga_ni_la_sube_de_peso(self):
        """Que el mecanismo haya acertado no vuelve a este trabajo el que lo observó.

        Si confirmarla la subiera a `W_SIGNAL_MATCH`, la frontera que ADR-004 defiende
        —observado contra anticipado— dejaría de existir después de la primera resolución.
        Si la apagara, resolver castigaría a quien resuelve.
        """
        (antes, _), (despues, motivos) = self._antes_y_despues("confirmed")
        self.assertIn("projected_match", motivos)
        # `assertAlmostEqual` y no `assertEqual`: entre las dos llamadas corre el reloj y
        # `W_DAY_DECAY` es continuo. Lo que se afirma es que el peso no cambió, no que el
        # tiempo no pase.
        self.assertAlmostEqual(despues, antes, places=5)


class InyeccionTest(IsolatedStoreTest):
    def _texto(self, estado):
        conn = store.connect()
        tid = _candidata(conn)
        store.resolve_projection(conn, store.projections_of(conn, tid)[0]["id"],
                                 status=estado, evidence="motivo suficiente",
                                 resolved_by="alguien")
        scored = retrieve.candidates(conn, task_type="debug_test_failure",
                                     repo_fingerprint=FP, cfg=config.load())
        texto, _ = retrieve.render(conn, scored, max_injected=3, native_memory=False,
                                   task_type="debug_test_failure", repo_fingerprint=FP)
        conn.close()
        return texto

    def test_una_confirmada_se_anuncia_como_confirmada_y_no_como_observada(self):
        texto = self._texto("confirmed")
        self.assertIn("CONFIRMADOS", texto)
        self.assertIn("siguen pesando la mitad", texto)
        self.assertIn(PROYECCIONES[0], texto)

    def test_una_refutada_se_cuenta_y_no_se_lista(self):
        """Que hubo trabajo ahí sí se dice; ofrecerla como síntoma a anticipar, no."""
        texto = self._texto("refuted")
        self.assertIn("refutadas", texto)
        self.assertNotIn(PROYECCIONES[0], texto)
        self.assertIn(PROYECCIONES[1], texto, "la otra sigue abierta y tiene que estar")


class AuditoriaTest(IsolatedStoreTest):
    def test_una_resolucion_que_perdio_su_evidencia_es_un_hallazgo(self):
        """Un veredicto sin origen no se acepta ni del modelo ni de una persona."""
        conn = store.connect()
        pid = store.projections_of(conn, _candidata(conn))[0]["id"]
        store.resolve_projection(conn, pid, status="confirmed", evidence="la vi pasar",
                                 resolved_by="alguien")
        conn.execute("UPDATE projections SET evidence = '' WHERE id = ?", (pid,))
        conn.commit()
        reporte = audit.audit_store(
            conn, redactor=redact.Redactor(identifiers=[],
                                           deny_paths=config.DEFAULT_DENY_PATHS,
                                           home_dir=None))
        conn.close()
        self.assertTrue([f for f in reporte["findings"]
                         if f["rule"] == "veredicto_sin_origen"])

    def test_una_conjetura_abierta_no_es_un_hallazgo(self):
        """Nadie la miró todavía, y eso es un estado legítimo, no una fuga."""
        conn = store.connect()
        _candidata(conn)
        reporte = audit.audit_store(
            conn, redactor=redact.Redactor(identifiers=[],
                                           deny_paths=config.DEFAULT_DENY_PATHS,
                                           home_dir=None))
        conn.close()
        self.assertEqual([f for f in reporte["findings"]
                          if f["rule"] == "veredicto_sin_origen"], [])


if __name__ == "__main__":
    unittest.main()
