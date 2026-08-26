"""SÃ­ntoma: los totales no cierran y el mismo cliente aparece dos veces."""

import unittest

from registro.reporte import totales


class ReporteTest(unittest.TestCase):
    def test_suma_las_dos_formas_en_una_sola_clave(self):
        filas = [{"clave": "acme srl", "valor": 100},
                 {"clave": "acme srl​", "valor": 50}]
        self.assertEqual(totales(filas), {"acme srl": 150})
