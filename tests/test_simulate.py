"""El ensayo end-to-end, y sobre todo lo que el ensayo no puede hacer.

Un ensayo que escribe en el store real inflaría el conteo de sesiones del gate de M1 con
sesiones inventadas. Eso no sería un atajo: sería evidencia fabricada. Hay un test de que
no lo hace.
"""

import unittest

from tests.base import IsolatedStoreTest
from nightshift import simulate, store


class SimulateTest(IsolatedStoreTest):
    def test_el_ensayo_completo_pasa_sin_modelo(self):
        reporte = simulate.run(con_modelo=False, noches=2, log=lambda _m: None)
        self.assertEqual(reporte["fallas"], [], "\n".join(reporte["fallas"]))

    def test_el_ensayo_no_escribe_en_el_store_ambiente(self):
        """El gate de M1 cuenta sesiones reales. Un ensayo no puede sumar a ese conteo."""
        simulate.run(con_modelo=False, noches=1, log=lambda _m: None)
        conn = store.connect()
        try:
            c = store.counts(conn)
        finally:
            conn.close()
        total = sum(c[k] for k in ("open", "closed", "candidate", "procedure",
                                   "superseded", "discarded"))
        self.assertEqual(total, 0, "el ensayo escribió en el store de esta sesión")
        self.assertEqual(c["steps"], 0)

    def test_lo_que_el_ensayo_afirma(self):
        reporte = simulate.run(con_modelo=False, noches=1, log=lambda _m: None)

        # Captura: sesiones distintas, deny_paths bloqueado, secreto redactado.
        self.assertGreaterEqual(reporte["auditoria"]["sessions"], 5)
        self.assertGreaterEqual(reporte["deny_path_hits"], 1)
        self.assertEqual(reporte["auditoria"]["findings"], [])

        # T3: la huérfana quedó cerrada.
        self.assertIn(reporte["huerfana"], ("closed", "discarded"))

        # T2: la sesión nueva recibió al menos una inyección por tipo de tarea, y
        # ninguna trayectoria dos veces.
        inyecciones = reporte["inyecciones_sesion_nueva"]
        self.assertTrue(any("same_task_type" in i["reason"] for i in inyecciones))
        fuentes = [i["source_trajectory"] for i in inyecciones]
        self.assertEqual(len(fuentes), len(set(fuentes)))

        # M3-b: las corridas nocturnas quedaron registradas.
        self.assertGreaterEqual(len(reporte["corridas"]), 1)

        # Y el store sigue sin fugas después de todo.
        self.assertEqual(reporte["auditoria_final"]["findings"], [])

    def test_el_secreto_sembrado_no_sobrevive(self):
        """El ensayo mete un secreto y un deny_path a propósito: si sobreviven, falla."""
        self.assertIn("tok_live", simulate.SECRETO)
        reporte = simulate.run(con_modelo=False, noches=1, log=lambda _m: None)
        self.assertNotIn(simulate.SECRETO, str(reporte))
        self.assertEqual(reporte["fallas"], [])


if __name__ == "__main__":
    unittest.main()
