"""Síntoma que reporta quien lo usa: algunos rótulos salen vacíos, sin ningún error."""

import unittest

from recolector.cadena import procesar


class RotuloTest(unittest.TestCase):
    def test_un_rotulo_imposible_no_queda_en_silencio(self):
        lecturas = [{"sensor": None, "magnitud": 1.0}]
        with self.assertRaises(Exception) as caso:
            procesar(lecturas)
        self.assertIn("rotular", str(caso.exception))
