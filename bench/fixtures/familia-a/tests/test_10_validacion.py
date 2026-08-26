"""SÃ­ntoma: una fila vÃ¡lida se rechaza."""

import unittest

from registro.validacion import es_valida


class ValidacionTest(unittest.TestCase):
    def test_acepta_una_accion_valida(self):
        self.assertTrue(es_valida({"accion": "Alta​"}))
