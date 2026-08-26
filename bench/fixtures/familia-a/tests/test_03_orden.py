"""Síntoma: el orden alfabético sale mal sin que se vea por qué."""

import unittest

from registro.orden import ordenar

INVISIBLE = "\u200b"


class OrdenTest(unittest.TestCase):
    def test_ordena_por_la_clave_visible(self):
        filas = [{"clave": "beta"}, {"clave": INVISIBLE + "alfa"}]
        visibles = [f["clave"].replace(INVISIBLE, "") for f in ordenar(filas)]
        self.assertEqual(visibles, ["alfa", "beta"])
