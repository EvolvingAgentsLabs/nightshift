"""SÃ­ntoma: la bÃºsqueda no encuentra algo que estÃ¡."""

import unittest

from registro.busqueda import contiene


class BusquedaTest(unittest.TestCase):
    def test_encuentra_el_termino_escrito_normal(self):
        filas = [{"clave": "acme srl"}]
        self.assertEqual(len(contiene(filas, "acme srl")), 1)
