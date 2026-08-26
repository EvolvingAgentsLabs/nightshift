"""SÃ­ntoma: la clave existe y `buscar` levanta KeyError."""

import unittest

from registro.indice import buscar, construir


class IndiceTest(unittest.TestCase):
    def test_encuentra_la_clave_aunque_venga_con_espacio_doble(self):
        indice = construir([{"clave": "acme srl", "valor": 10}])
        self.assertEqual(buscar(indice, "ACME  SRL")["valor"], 10)
