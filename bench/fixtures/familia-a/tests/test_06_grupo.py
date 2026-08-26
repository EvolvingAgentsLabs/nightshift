"""SÃ­ntoma: un grupo aparece partido en dos."""

import unittest

from registro.grupo import agrupar


class GrupoTest(unittest.TestCase):
    def test_no_parte_el_grupo(self):
        filas = [{"clave": "acme srl"}, {"clave": " acme srl "}]
        self.assertEqual(len(agrupar(filas)), 1)
