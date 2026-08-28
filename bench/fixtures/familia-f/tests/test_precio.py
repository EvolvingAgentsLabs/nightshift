import unittest

from servicio import catalogo


class PrecioTest(unittest.TestCase):
    def setUp(self):
        self.cache = catalogo.reiniciar()

    def _buscar(self, producto, moneda):
        return {"ars": 1000, "usd": 1}[moneda]

    def test_dos_monedas_dan_dos_precios(self):
        p = {"id": "sku-1"}
        self.assertEqual(catalogo.precio(p, "ars", self._buscar), 1000)
        self.assertEqual(catalogo.precio(p, "usd", self._buscar), 1)

    def test_el_cache_sigue_sirviendo(self):
        """Apagar el cache hace pasar el test de arriba y rompe éste."""
        p = {"id": "sku-2"}
        catalogo.precio(p, "ars", self._buscar)
        catalogo.precio(p, "ars", self._buscar)
        self.assertGreater(self.cache.aciertos, 0,
                           "el cache no acerto nunca: esta apagado o la clave cambia sola")


if __name__ == "__main__":
    unittest.main()
