"""La suite se audita a sí misma: ningún archivo de tests puede aportar cero.

De dónde sale este archivo: dream, ideando sobre trayectorias reales de este repo, dibujó
el mecanismo de una falla de importación como **un cambio de coordenadas que hace
desaparecer un término**, y de ahí sacó cuál es la magnitud que se pierde en todo el
recorrido:

    «Se conserva la forma del veredicto: siempre sale un OK, un conteo, un exit code. Lo
    que se pierde en cada etapa, sin que nadie se queje, es N: cuántas aserciones
    efectivamente se ejecutaron. Verde no significa "nada se rompió", significa "nada de
    lo que llegó a correr se rompió".»

Y proyectó el síntoma: *«un test recién agregado no se ejecuta nunca y nadie lo advierte,
porque el total no se compara contra ningún valor esperado».* Comprobado contra este repo
el 2026-08-27: cierto. `make test` corre `unittest discover -q`, que sale 0 con los tests
que haya — y ningún archivo aportaba cero **ese día**, que no es lo mismo que estar
protegido.

Es el mismo modo de falla que ya costó dos milestones acá: la captura guardaba estructura
vacía y no fallaba nunca, porque los hooks salen 0 pase lo que pase. Un archivo que deja
de ser descubierto —renombrado, movido, con sus tests comentados— baja el total en
silencio y deja en verde un gate que dejó de mirar.

Esto no reemplaza a `make check`: le agrega la pregunta que le faltaba, que es **cuántos**
y no sólo **cómo salieron**.
"""

import unittest
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
TESTS = RAIZ / "tests"


def _contar(suite) -> int:
    total = 0
    for item in suite:
        total += _contar(item) if isinstance(item, unittest.TestSuite) else 1
    return total


class SuiteTest(unittest.TestCase):
    def test_ningun_archivo_de_tests_aporta_cero(self):
        """Un archivo que deja de aportar baja el total sin que nada se queje."""
        archivos = sorted(p.stem for p in TESTS.glob("test_*.py"))
        self.assertTrue(archivos, "no se encontró ningún archivo de tests")
        vacios = []
        for nombre in archivos:
            cargados = unittest.defaultTestLoader.loadTestsFromName("tests.%s" % nombre)
            if _contar(cargados) == 0:
                vacios.append(nombre)
        self.assertEqual(vacios, [],
                         "estos archivos existen y no aportan ni un test: %s" % vacios)

    def test_el_descubrimiento_ve_todos_los_archivos(self):
        """`discover` puede saltear un archivo sin decirlo: por nombre, por paquete roto.

        La diferencia entre "los tests pasan" y "los tests que se descubrieron pasan" es
        justamente la magnitud que el dibujo dice que se pierde.
        """
        descubiertos = _contar(
            unittest.defaultTestLoader.discover(str(TESTS), top_level_dir=str(RAIZ)))
        uno_por_uno = sum(
            _contar(unittest.defaultTestLoader.loadTestsFromName("tests.%s" % p.stem))
            for p in sorted(TESTS.glob("test_*.py")))
        self.assertEqual(descubiertos, uno_por_uno,
                         "`discover` ve %d y los archivos suman %d: hay un archivo que "
                         "el descubrimiento se está salteando"
                         % (descubiertos, uno_por_uno))


if __name__ == "__main__":
    unittest.main()
