"""Síntoma: las consultas cortan al segundo aunque los ajustes digan 2000 ms."""

import unittest

from servicio.ajustes import LIMITES
from servicio import red


class Cliente:
    def __init__(self):
        self.visto = None

    def pedir(self, tiempo_limite):
        self.visto = tiempo_limite
        return "ok"


class ConsultaTest(unittest.TestCase):
    def test_usa_el_limite_de_los_ajustes(self):
        cliente = Cliente()
        red.consultar(cliente)
        self.assertEqual(cliente.visto, LIMITES["consulta_ms"])
