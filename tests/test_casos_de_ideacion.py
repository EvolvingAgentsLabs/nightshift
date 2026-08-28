"""Los casos de ideación de referencia pasan los gates reales — o no son referencia.

`experimentos/casos_de_ideacion.py` es material **diseñado**: seis mecanismos con su
ideación completa escrita a mano, que después se montan como sintéticos para medir el techo
del brazo `fisica` a escala. Un caso de referencia que no pasa los gates del plugin no es
una referencia: es el mismo deseo sin gate que los casos existen para evitar.

Esto corre en `make check` a propósito: si un gate del brazo se endurece —una palabra nueva
en el vocabulario prohibido, un tope distinto— y algún caso deja de pasar, tiene que
fallar el gate del repo, no descubrirse la próxima vez que alguien corra el experimento.
"""

import importlib.util
import unittest
from pathlib import Path

from nightshift import config, dream, redact

RAIZ = Path(__file__).resolve().parent.parent


def _casos():
    ruta = RAIZ / "experimentos" / "casos_de_ideacion.py"
    spec = importlib.util.spec_from_file_location("casos_de_ideacion", ruta)
    modulo = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(modulo)
    return modulo


def _redactor():
    return redact.Redactor(identifiers=[], deny_paths=config.DEFAULT_DENY_PATHS,
                           home_dir=None)


class CasosDeReferenciaTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.modulo = _casos()
        cls.casos = cls.modulo.CASOS

    def test_hay_casos_y_cada_uno_esta_entero(self):
        self.assertGreaterEqual(len(self.casos), 4)
        for caso in self.casos:
            with self.subTest(caso=caso.get("slug")):
                for campo in ("slug", "mecanismo", "physical_scene", "logogram",
                              "pattern", "signals", "valid_when", "projected_signals",
                              "parafrasis"):
                    self.assertTrue(caso.get(campo), "falta `%s`" % campo)

    def test_los_slugs_y_los_logogramas_no_se_repiten(self):
        """Dos casos con el mismo signo no son dos casos: son uno contado dos veces."""
        slugs = [c["slug"] for c in self.casos]
        logogramas = [c["logogram"] for c in self.casos]
        self.assertEqual(len(slugs), len(set(slugs)))
        self.assertEqual(len(logogramas), len(set(logogramas)))

    def test_cada_caso_pasa_los_gates_del_brazo_fisico(self):
        """El gate real, no una versión parecida: `dream.validate` con `modo=fisica`.

        Si esto falla, o el caso está mal escrito o un gate se endureció — y las dos
        cosas hay que saberlas en `make check`, no en la próxima corrida del experimento.
        """
        redactor = _redactor()
        for caso in self.casos:
            with self.subTest(caso=caso["slug"]):
                abstraction, valid_when, _, problemas = dream.validate(
                    {"pattern": caso["pattern"], "signals": caso["signals"],
                     "valid_when": caso["valid_when"],
                     "projected_signals": caso["projected_signals"],
                     "physical_scene": caso["physical_scene"],
                     "logogram": caso["logogram"]},
                    redactor=redactor, home_dir=None, modo="fisica")
                self.assertEqual(problemas, [])
                self.assertEqual(abstraction["_physical_scene"],
                                 " ".join(caso["physical_scene"].split()))
                self.assertEqual(abstraction["_logogram"], caso["logogram"])
                self.assertTrue(valid_when)

    def test_la_parafrasis_no_copia_una_senal(self):
        """La regla del protocolo de retenidos, en su versión mínima y automatizable.

        Las paráfrasis de estos casos las escribió quien mide —por eso esto es un techo—
        pero al menos no pueden ser una señal copiada: si la paráfrasis ES una señal, el
        experimento mide la identidad y ni siquiera es un techo, es un espejo.
        """
        for caso in self.casos:
            with self.subTest(caso=caso["slug"]):
                superficie = [s.lower() for s in caso["signals"]]
                self.assertNotIn(caso["parafrasis"].lower().strip(), superficie)


if __name__ == "__main__":
    unittest.main()
