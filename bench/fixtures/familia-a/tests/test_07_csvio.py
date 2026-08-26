"""SÃ­ntoma: el ida y vuelta por CSV no devuelve la misma clave."""

import unittest

from registro.csvio import ida_y_vuelta


class CsvTest(unittest.TestCase):
    def test_la_clave_sobrevive_igual_al_ida_y_vuelta(self):
        filas = [{"clave": "acme  srl", "valor": 3}]
        self.assertEqual(ida_y_vuelta(filas), ["acme srl"])
