"""SÃ­ntoma: quedan duplicados que deberÃ­an haberse colapsado."""

import unittest

from registro.dedup import unicos


class DedupTest(unittest.TestCase):
    def test_colapsa_dos_formas_de_la_misma_clave(self):
        filas = [{"clave": "acme srl"}, {"clave": "acme srl​"}]
        self.assertEqual(len(unicos(filas)), 1)
