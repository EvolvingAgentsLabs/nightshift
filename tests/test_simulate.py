"""El ensayo end-to-end, y sobre todo lo que el ensayo no puede hacer.

Un ensayo que escribe en el store real inflaría el conteo de sesiones del gate de M1 con
sesiones inventadas. Eso no sería un atajo: sería evidencia fabricada. Hay un test de que
no lo hace.
"""

import os
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

    def test_el_modelo_corre_con_el_home_que_se_le_da(self):
        """El backend por defecto es un agente con credenciales en el HOME (ADR-003).

        Sin esto, el ensayo —que reemplaza `HOME` para no instalar un timer de verdad— le
        sacaba la sesión al modelo: `claude -p` salía 1 con stderr vacío y el ensayo lo
        reportaba como "dream no produjo ninguna candidata".
        """
        from nightshift import dream

        modelo = dream.LocalModel(["/bin/sh", "-c", 'printf %s "$HOME"'],
                                  home="/tmp/el-home-de-verdad")
        self.assertEqual(modelo.ask("lo que sea"), "/tmp/el-home-de-verdad")

    def test_el_ensayo_le_pasa_al_modelo_el_home_real(self):
        """Y el ensayo tiene que pasarle el de antes de reemplazarlo, no el suyo."""
        from nightshift import dream

        vistos = []
        original = dream.LocalModel

        class Espia(original):
            def __init__(self, command, timeout=None, home=None):
                vistos.append(home)
                super().__init__(command, timeout=timeout or 30, home=home)

            def ask_json(self, prompt):
                return {"pattern": None}      # sin patrón: el ensayo sigue su curso

        real = os.environ.get("HOME")
        dream.LocalModel = Espia
        try:
            simulate.run(con_modelo=True, noches=1, log=lambda _m: None)
        finally:
            dream.LocalModel = original
        self.assertTrue(vistos, "el ensayo no construyó ningún modelo")
        self.assertEqual(vistos[0], real,
                         "el modelo recibió el HOME del ensayo, no el de la máquina")

    def test_el_secreto_sembrado_no_sobrevive(self):
        """El ensayo mete un secreto y un deny_path a propósito: si sobreviven, falla."""
        self.assertIn("tok_live", simulate.SECRETO)
        reporte = simulate.run(con_modelo=False, noches=1, log=lambda _m: None)
        self.assertNotIn(simulate.SECRETO, str(reporte))
        self.assertEqual(reporte["fallas"], [])


if __name__ == "__main__":
    unittest.main()
