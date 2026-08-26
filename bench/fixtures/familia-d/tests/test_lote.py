"""Síntoma: los lotes cortan a los 5 segundos aunque los ajustes digan 8000 ms."""

import unittest

from servicio.ajustes import LIMITES
from servicio import red


class Cliente:
    def __init__(self):
        self.visto = None

    def despachar(self, tiempo_limite):
        self.visto = tiempo_limite
        return "ok"


class LoteTest(unittest.TestCase):
    def test_usa_el_limite_de_los_ajustes(self):
        cliente = Cliente()
        red.lote(cliente)
        self.assertEqual(cliente.visto, LIMITES["lote_ms"])
