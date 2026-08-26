"""Síntoma: las escrituras cortan al segundo aunque los ajustes digan 4000 ms."""

import unittest

from servicio.ajustes import LIMITES
from servicio import red


class Cliente:
    def __init__(self):
        self.visto = None

    def enviar(self, tiempo_limite):
        self.visto = tiempo_limite
        return "ok"


class EscrituraTest(unittest.TestCase):
    def test_usa_el_limite_de_los_ajustes(self):
        cliente = Cliente()
        red.escribir(cliente)
        self.assertEqual(cliente.visto, LIMITES["escritura_ms"])
