"""Lo que llega al soporte: hay libros ausentes del listado final, y nadie vio un error."""

import unittest

from catalogo.secuencia import ejecutar


class IndiceTest(unittest.TestCase):
    def test_un_paso_roto_debe_interrumpir_la_corrida(self):
        fichas = [{"titulo": "Cien años de soledad", "anio": "1967"}]
        with self.assertRaises(Exception) as detalle:
            ejecutar(fichas)
        self.assertIn("decada", str(detalle.exception),
                      "la excepción debe identificar el paso responsable")
