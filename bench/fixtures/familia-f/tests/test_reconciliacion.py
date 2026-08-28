import unittest

from servicio.reconciliar import Libro, reconciliar


class ReconciliacionTest(unittest.TestCase):
    def test_lote_grande_no_se_cae(self):
        """500 movimientos tienen que reconciliar dentro del límite."""
        movimientos = [{"cuenta": "c%03d" % i} for i in range(500)]
        libro = Libro()
        salida = reconciliar(movimientos, libro=libro)
        self.assertEqual(len(salida), 500)


if __name__ == "__main__":
    unittest.main()
