"""SÃ­ntoma: el join pierde filas en silencio."""

import unittest

from registro.union import unir


class UnionTest(unittest.TestCase):
    def test_une_las_dos_formas_de_la_misma_clave(self):
        izquierda = [{"clave": "acme srl", "valor": 1}]
        derecha = [{"clave": "acme srl", "valor": 2}]
        self.assertEqual(len(unir(izquierda, derecha)), 1)
