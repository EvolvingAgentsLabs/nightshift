"""Síntoma que reporta quien lo usa: el promedio da 0 y los datos de entrada están bien."""

import unittest

from recolector.cadena import procesar


class PromedioTest(unittest.TestCase):
    def test_una_etapa_que_falla_no_se_traga_el_error(self):
        lecturas = [{"sensor": "norte", "magnitud": "2.5"}]
        with self.assertRaises(Exception) as caso:
            procesar(lecturas)
        self.assertIn("redondear", str(caso.exception),
                      "el error tiene que decir en qué etapa se rompió")
