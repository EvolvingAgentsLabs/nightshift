"""Lo que llega al soporte: hay libros con encabezado en blanco y el año puesto en cero."""

import unittest

from catalogo.secuencia import ejecutar


class EncabezadoTest(unittest.TestCase):
    def test_un_encabezado_imposible_debe_interrumpir_la_corrida(self):
        fichas = [{"titulo": None, "anio": 1967}]
        with self.assertRaises(Exception) as detalle:
            ejecutar(fichas)
        self.assertIn("acortar", str(detalle.exception))
