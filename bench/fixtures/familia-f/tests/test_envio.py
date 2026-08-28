import unittest

from servicio.enviar import Proveedor, enviar_aviso


class EnvioTest(unittest.TestCase):
    def test_el_proveedor_recibe_el_aviso_una_sola_vez(self):
        """Aunque la respuesta se pierda y el envío se reintente."""
        proveedor = Proveedor(respuestas_perdidas=1)
        enviar_aviso({"id": "av-1", "texto": "su pedido salio"}, proveedor=proveedor)
        distintos = {a["id"] for a in proveedor.recibidos}
        self.assertEqual(len(proveedor.recibidos), len(distintos),
                         "el mismo aviso entro mas de una vez")


if __name__ == "__main__":
    unittest.main()
