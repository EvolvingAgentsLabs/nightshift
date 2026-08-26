"""SÃ­ntoma: el cache no acierta nunca y todo se recalcula."""

import unittest

from registro.cache import Cache


class CacheTest(unittest.TestCase):
    def test_la_segunda_consulta_acierta(self):
        cache = Cache()
        cache.obtener("acme srl", lambda c: 1)
        cache.obtener("acme  srl", lambda c: 1)
        self.assertEqual((cache.aciertos, cache.fallos), (1, 1))
