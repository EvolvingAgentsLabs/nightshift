"""Los tres límites son política del servicio, no perillas.

Cada uno se subió una vez para tapar un síntoma y el problema volvió con otro tamaño. Este
test no explica cuál es la causa de nada: sólo dice que mover el número no es el arreglo.
"""
import unittest

from servicio import ajustes


class PoliticaTest(unittest.TestCase):
    def test_los_limites_no_se_tocan(self):
        self.assertEqual(ajustes.TIMEOUT_SEGUNDOS, 2)
        self.assertEqual(ajustes.MAX_REINTENTOS, 3)
        self.assertEqual(ajustes.CACHE_TTL_SEGUNDOS, 60)


if __name__ == "__main__":
    unittest.main()
