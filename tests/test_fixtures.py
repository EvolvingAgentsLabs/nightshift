"""Los fixtures del benchmark: que sean fixtures, y no decoración.

Un fixture puede estar roto de tres maneras silenciosas, y las tres arruinan la medición
sin romper nada:

1. una tarea que **ya pasa** antes de que el agente toque nada;
2. una tarea que **no se puede resolver**, y entonces todas las filas empatan en cero;
3. en la familia C, dos repos que **comparten vocabulario**, y entonces lo que se mide es
   la coincidencia de palabras y no la transferencia.

Los gates reales (correr cada tarea antes y después del fix de referencia) están en
`nightshift bench fixtures` / `make bench-fixtures`, que arranca un intérprete por tarea
y no corresponde meter en `make check`. Acá va lo estructural, que es rápido.
"""

import builtins
import json
import keyword
import re
import unittest
from pathlib import Path

from nightshift import bench

ROOT = Path(__file__).resolve().parent.parent
FIXTURES = ROOT / "bench" / "fixtures"

# Lo que dos repos de Python comparten sí o sí sin que eso sea vocabulario del dominio.
PERMITIDOS = set(keyword.kwlist) | set(dir(builtins)) | {
    "self", "unittest", "assertIn", "assertRaises", "assertEqual", "TestCase",
    "__name__", "__init__", "append", "exception", "python3", "cada", "error",
}


def identificadores(directorio):
    tokens = set()
    for archivo in Path(directorio).rglob("*.py"):
        for token in re.findall(r"[A-Za-zÁ-úñÑ_][A-Za-zÁ-úñÑ_0-9]*",
                                archivo.read_text(encoding="utf-8")):
            if len(token) >= 4 and token not in PERMITIDOS:
                tokens.add(token.lower())
    return tokens


class FixturesTest(unittest.TestCase):
    def fixtures(self):
        return sorted(FIXTURES.glob("*/fixture*.json"))

    def test_todos_cargan_y_declaran_lo_necesario(self):
        vistos = set()
        for ruta in self.fixtures():
            with self.subTest(fixture=ruta.name):
                fixture = bench.load_fixture(ruta)
                vistos.add(fixture["family"])
                self.assertTrue(fixture["tasks"])
                self.assertIn(fixture["family"], bench.FAMILIES)
                for task in fixture["tasks"]:
                    self.assertIn("prompt", task, "una tarea sin prompt no es una tarea")
        self.assertEqual(vistos, set(bench.FAMILIES),
                         "faltan fixtures para alguna familia del pre-registro")

    def test_cada_tarea_declara_como_probar_que_es_resoluble(self):
        """Sin fix de referencia no se puede afirmar que la tarea tenga solución."""
        for ruta in self.fixtures():
            if "selftest" in str(ruta):
                continue
            fixture = bench.load_fixture(ruta)
            for task in fixture["tasks"]:
                with self.subTest(fixture=fixture["name"], task=task["id"]):
                    self.assertTrue(task.get("reference_fix") or fixture.get("reference_fix"))

    def test_familia_a_tiene_diez_bugs_y_una_sola_causa(self):
        fixture = bench.load_fixture(FIXTURES / "familia-a" / "fixture.json")
        self.assertEqual(len(fixture["tasks"]), 10, "PREREG §3-A pide 10 bugs")
        sintomas = {t["symptom"] for t in fixture["tasks"]}
        self.assertEqual(len(sintomas), 10, "diez síntomas distintos, no diez veces el mismo")
        # Una sola causa: todos los fixes de referencia tocan el mismo archivo.
        destinos = {tuple(t.get("reference_fix", fixture["reference_fix"])["apply"])
                    for t in fixture["tasks"]}
        self.assertEqual(len(destinos), 1, "la causa compartida es un solo archivo")

    def test_familia_c_no_comparte_vocabulario_entre_repos(self):
        """Si el test del repo B usa las palabras del A, se mide el vocabulario, no la memoria."""
        base = FIXTURES / "familia-c"
        alfa, beta = identificadores(base / "repo-alfa"), identificadores(base / "repo-beta")
        self.assertTrue(alfa and beta)
        self.assertEqual(alfa & beta, set(),
                         "los dos repos comparten identificadores: %s" % sorted(alfa & beta))

    def test_familia_c_no_comparte_rutas(self):
        base = FIXTURES / "familia-c"
        rutas = {}
        for repo in ("repo-alfa", "repo-beta"):
            rutas[repo] = {str(p.relative_to(base / repo))
                           for p in (base / repo).rglob("*") if p.is_file()}
        self.assertEqual(rutas["repo-alfa"] & rutas["repo-beta"], set())

    def test_familia_c_no_rota_el_orden(self):
        """Rotar mete tareas del repo B en la fase de aprendizaje: exposición previa."""
        fixture = bench.load_fixture(FIXTURES / "familia-c" / "fixture.json")
        self.assertTrue(fixture.get("fixed_order"))
        for seed in (None, "x", "42", "cualquier-cosa"):
            with self.subTest(seed=seed):
                celdas = bench.matrix(fixture, rows=("S0",), repeats=1, seed=seed)
                aprendizaje = [c["task"] for c in celdas if c["phase"] == "learning"]
                medicion = [c["task"] for c in celdas if c["phase"] == "measure"]
                self.assertTrue(all(t.startswith("alfa_") for t in aprendizaje),
                                "se aprende en el repo A")
                self.assertTrue(all(t.startswith("beta_") for t in medicion),
                                "se mide en el repo B")

    def test_familia_d_trae_su_ground_truth_y_su_clasificador(self):
        base = FIXTURES / "familia-d"
        fixture = bench.load_fixture(base / "fixture.json")
        self.assertTrue(fixture.get("classify"), "§3-D exige un script determinista")
        verdad = json.loads((base / "verdad.json").read_text(encoding="utf-8"))
        historia = json.loads((base / "historia.json").read_text(encoding="utf-8"))
        self.assertEqual({item["claim"] for item in historia}, set(verdad),
                         "cada trayectoria sembrada tiene su veredicto en el ground truth")
        estados = {v["estado"] for v in verdad.values()}
        self.assertIn("falsa", estados, "la familia D necesita al menos una falsa")
        self.assertIn("stale", estados, "y al menos una stale")
        for item in verdad.values():
            self.assertTrue(item.get("motivo"), "un veredicto sin motivo no es ground truth")

    def test_los_fixtures_reales_no_se_confunden_con_el_del_selftest(self):
        readme = (FIXTURES / "selftest" / "README.md").read_text(encoding="utf-8")
        self.assertIn("no es un fixture del benchmark", readme.lower())
        for familia in ("familia-a", "familia-c", "familia-d"):
            texto = (FIXTURES / familia / "README.md").read_text(encoding="utf-8")
            self.assertIn("TODO(Matias)", texto,
                          "el README tiene que decir que falta congelarlo")


if __name__ == "__main__":
    unittest.main()


class PropuestasTest(unittest.TestCase):
    """Fixtures construidos para familias que el pre-registro todavía no abrió.

    Se llaman `propuesta.json` y no `fixture.json` a propósito: `bench.FAMILIES` es lo que
    el runner sabe correr, y `make check` afirma que los fixtures del benchmark son
    exactamente las familias que `PREREG` declara. Un fixture de una familia que nadie
    congeló no es un fixture del benchmark todavía — es una propuesta, y el nombre del
    archivo lo dice. Cuando Matías abra la sección, se renombra y entra por el camino de
    arriba.

    Este test existe para que no se pudran mientras esperan.
    """

    def propuestas(self):
        return sorted(FIXTURES.glob("*/propuesta.json"))

    def test_las_propuestas_declaran_lo_mismo_que_un_fixture(self):
        for ruta in self.propuestas():
            with self.subTest(propuesta=ruta.parent.name):
                data = json.loads(ruta.read_text(encoding="utf-8"))
                self.assertTrue(data.get("tasks"), "una propuesta sin tareas no propone nada")
                self.assertIn("note", data, "tiene que decir que es una propuesta")
                self.assertNotIn(data["family"], bench.FAMILIES,
                                 "si la familia ya está en el pre-registro, esto es un "
                                 "fixture y va con su nombre")
                for task in data["tasks"]:
                    self.assertIn("id", task)
                    self.assertIn("prompt", task)
                    self.assertIn("symptom", task)
                self.assertTrue((ruta.parent / "gate.sh").is_file(),
                                "sin gate no se puede afirmar nada de la tarea")
