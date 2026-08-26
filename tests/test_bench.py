"""Runner del benchmark de M4.

Lo que estos tests defienden no es que el benchmark dé bien: es que el runner **no
decida nada**. Un umbral que se ajusta después de ver el resultado no es un umbral, y la
forma más cómoda de ajustarlo sin darse cuenta es un runner que corre igual con el
pre-registro abierto.

Por eso hay un test de que el pre-registro real de este repo sigue sin congelar y con sus
`TODO(Matias)` intactos: si alguien —persona o agente— los completa, este test lo dice.

El gate del runner con el pipeline entero es `nightshift bench selftest`.
"""

import contextlib
import io
import json
import unittest
from pathlib import Path

from tests.base import IsolatedStoreTest
from nightshift import bench, cli

ROOT = Path(__file__).resolve().parent.parent
PREREG = ROOT / "bench" / "PREREG.md"
FIXTURES = ROOT / "bench" / "fixtures" / "selftest"

CONGELADO = """# PREREG de prueba

| Campo | Valor |
|---|---|
| Estado | CONGELADO |

### A — Bug recurrente variado

| Métrica | Umbral de go (S1 vs S0) |
|---|---|
| Tasa de resolución | +20 pp |

### C — Transferencia cross-repo

| Métrica | Umbral de go (S1 vs S0) |
|---|---|
| Tasa de resolución en repo B | +20 pp |

### D — Precisión de consolidación

| Métrica | Umbral de go (S1 vs S0) |
|---|---|
| Proporción de memorias falsas o stale | -10 pp |
"""


class PreregTest(unittest.TestCase):
    def test_el_prereg_real_sigue_sin_congelar_y_con_sus_todos(self):
        """Si esto falla, alguien completó decisiones que no son suyas."""
        prereg = bench.read_prereg(PREREG)
        self.assertFalse(prereg["frozen"], "el pre-registro real no está congelado")
        self.assertGreaterEqual(len(prereg["todos"]), 19)
        self.assertEqual({t["owner"] for t in prereg["todos"]}, {"Matias"})
        for familia in bench.FAMILIES:
            fila = bench.primary_threshold(prereg, familia)
            self.assertIsNotNone(fila, "familia %s sin tabla de umbrales" % familia)
            self.assertIsNone(fila["threshold"],
                              "familia %s tiene un umbral fijado y no debería" % familia)

    def test_el_prereg_real_no_esta_listo_para_correr(self):
        estado = bench.readiness(bench.read_prereg(PREREG))
        self.assertFalse(estado["ready"])
        self.assertTrue(any("no está congelado" in b for b in estado["blockers"]))
        self.assertTrue(any("TODO" in b for b in estado["blockers"]))

    def test_gramatica_de_umbrales(self):
        casos = {
            "+10 pp": ("pp", 10.0), "-15 pp": ("pp", -15.0), "+15%": ("pct", 15.0),
            ">= 0.30": ("gte", 0.30), "≤ 0.2": ("lte", 0.2),
        }
        for raw, (kind, value) in casos.items():
            with self.subTest(raw=raw):
                umbral = bench.parse_threshold(raw)
                self.assertIsNotNone(umbral, raw)
                self.assertEqual((umbral.kind, umbral.value), (kind, value))

    def test_un_umbral_que_no_se_entiende_no_se_adivina(self):
        for raw in ("`TODO(Matias)`", "bastante mejor", "", "10 bananas", "mejor que S0"):
            with self.subTest(raw=raw):
                self.assertIsNone(bench.parse_threshold(raw))

    def test_un_umbral_ilegible_bloquea_la_corrida(self):
        """Ilegible no es "más o menos": bloquea igual que ausente."""
        import tempfile

        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        path = Path(tmp.name) / "prereg.md"
        path.write_text(CONGELADO.replace("+20 pp", "bastante mejor", 1), encoding="utf-8")
        estado = bench.readiness(bench.read_prereg(path))
        self.assertFalse(estado["ready"])
        self.assertTrue(any("no se entiende" in b for b in estado["blockers"]))


class DecisionTest(unittest.TestCase):
    def prereg(self):
        import tempfile

        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        path = Path(tmp.name) / "prereg.md"
        path.write_text(CONGELADO, encoding="utf-8")
        return bench.read_prereg(path)

    def summary(self, **kwargs):
        base = {("A", "S0"): {"resolution_rate": 0.4, "false_stale_ratio": None},
                ("A", "S1"): {"resolution_rate": 0.8, "false_stale_ratio": None},
                ("C", "S0"): {"resolution_rate": 0.3, "false_stale_ratio": None},
                ("C", "S1"): {"resolution_rate": 0.7, "false_stale_ratio": None},
                ("D", "S0"): {"resolution_rate": None, "false_stale_ratio": 0.40},
                ("D", "S1"): {"resolution_rate": None, "false_stale_ratio": 0.10}}
        base.update(kwargs)
        return base

    def test_tres_familias_alcanzan_es_go(self):
        veredicto = bench.decide(self.summary(), self.prereg())
        self.assertTrue(veredicto["go"])
        self.assertEqual(sorted(veredicto["familias_alcanzadas"]), ["A", "C", "D"])

    def test_una_sola_familia_no_alcanza_para_go(self):
        resumen = self.summary()
        resumen[("C", "S1")] = {"resolution_rate": 0.31, "false_stale_ratio": None}
        resumen[("D", "S1")] = {"resolution_rate": None, "false_stale_ratio": 0.39}
        veredicto = bench.decide(resumen, self.prereg())
        self.assertFalse(veredicto["go"], "la regla pide ≥2 de 3 familias")

    def test_en_D_menor_es_mejor(self):
        resumen = self.summary()
        resumen[("D", "S1")] = {"resolution_rate": None, "false_stale_ratio": 0.90}
        veredicto = bench.decide(resumen, self.prereg())
        self.assertFalse(veredicto["por_familia"]["D"]["met"],
                         "empeorar la proporción de memoria falsa no puede alcanzar")

    def test_sin_dato_es_indecidible_no_es_go(self):
        resumen = {k: v for k, v in self.summary().items() if k[0] != "D"}
        veredicto = bench.decide(resumen, self.prereg())
        self.assertIsNone(veredicto["go"])
        self.assertEqual(veredicto["indecidibles"], ["D"])

    def test_sin_umbral_es_indecidible_no_es_go(self):
        veredicto = bench.decide(self.summary(), bench.read_prereg(PREREG))
        self.assertIsNone(veredicto["go"], "indecidible no es no-go, y no es go")
        self.assertEqual(sorted(veredicto["indecidibles"]), ["A", "C", "D"])


class MatrixTest(unittest.TestCase):
    def fixture(self):
        return bench.load_fixture(FIXTURES / "fixture-a.json")

    def test_la_matriz_tiene_la_forma_del_prereg(self):
        celdas = bench.matrix(self.fixture(), repeats=3, seed="x")
        self.assertEqual(len(celdas), 2 * 3 * 4, "2 filas × 3 corridas × 4 tareas")
        self.assertEqual({c["row"] for c in celdas}, {"S0", "S1"})

    def test_el_orden_es_el_mismo_en_todas_las_filas(self):
        """Mitigación §5: el orden no puede favorecer a una fila."""
        celdas = bench.matrix(self.fixture(), repeats=1, seed="semilla")
        s0 = [c["task"] for c in celdas if c["row"] == "S0"]
        s1 = [c["task"] for c in celdas if c["row"] == "S1"]
        self.assertEqual(s0, s1)

    def test_el_orden_es_reproducible_y_depende_del_seed(self):
        primero = [c["task"] for c in bench.matrix(self.fixture(), repeats=1, seed="a")]
        otra_vez = [c["task"] for c in bench.matrix(self.fixture(), repeats=1, seed="a")]
        distinto = [c["task"] for c in bench.matrix(self.fixture(), repeats=1, seed="zzz")]
        self.assertEqual(primero, otra_vez, "mismo seed, mismo orden, en cualquier máquina")
        self.assertNotEqual(primero, distinto)

    def test_la_fase_de_aprendizaje_son_las_primeras_tareas(self):
        celdas = bench.matrix(self.fixture(), repeats=1, seed=None)
        fases = [c["phase"] for c in celdas if c["row"] == "S0"]
        self.assertEqual(fases, ["learning", "learning", "measure", "measure"])

    def test_la_fila_S2_esta_bloqueada_hasta_M5(self):
        with self.assertRaises(ValueError) as caso:
            bench.matrix(self.fixture(), rows=("S0", "S2"))
        self.assertIn("M5", str(caso.exception))

    def test_un_fixture_mal_formado_no_se_corre_a_medias(self):
        import tempfile

        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        malo = Path(tmp.name) / "fixture.json"
        for contenido in ('{"name": "x", "family": "A", "gate": ["true"]}',
                          '{"name": "x", "family": "Z", "gate": ["true"], "tasks": [{"id": "t"}]}',
                          '{"name": "x", "family": "A", "gate": ["true"], "tasks": []}'):
            malo.write_text(contenido, encoding="utf-8")
            with self.subTest(contenido=contenido):
                with self.assertRaises(bench.FixtureError):
                    bench.load_fixture(malo)


class CliTest(IsolatedStoreTest):
    def run_cli(self, argv):
        out, err = io.StringIO(), io.StringIO()
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
            code = cli.main(argv)
        return code, out.getvalue(), err.getvalue()

    def test_check_dice_que_falta_y_sale_1(self):
        code, out, _ = self.run_cli(["bench", "check"])
        self.assertEqual(code, 1)
        self.assertIn("listo para correr: NO", out)
        self.assertIn("TODO pendientes", out)
        self.assertIn("no propone, no completa ni ajusta umbrales", out)

    def test_run_se_niega_con_el_prereg_real(self):
        code, _, err = self.run_cli(
            ["bench", "run", "--fixture", str(FIXTURES / "fixture-a.json"),
             "--agent", "./agent.sh {task} {row}"])
        self.assertEqual(code, 3, "correr con el pre-registro abierto está prohibido")
        self.assertIn("No se corre nada", err)
        self.assertIn("no es un umbral", err)

    def test_plan_no_es_correr(self):
        code, out, _ = self.run_cli(["bench", "plan", "--fixture",
                                     str(FIXTURES / "fixture-a.json"), "--repeats", "1"])
        self.assertEqual(code, 0, "planificar con el pre-registro abierto sí se puede")
        self.assertIn("celdas    : 8", out)
        self.assertIn("va a negarse", out)

    def test_check_json(self):
        code, out, _ = self.run_cli(["bench", "check", "--json"])
        data = json.loads(out)
        self.assertEqual(code, 1)
        self.assertFalse(data["readiness"]["ready"])
        self.assertGreaterEqual(len(data["prereg"]["todos"]), 19)

    def test_la_ruta_de_trabajo_es_estable_dentro_de_una_repeticion(self):
        """Las dos memorias que se comparan keyean por ruta.

        Auto Memory por ruta de proyecto y nightshift por fingerprint del repo. Con una
        ruta nueva por tarea ninguna acumula nada y la fase de aprendizaje no existe. Y
        con ruta nueva sólo para S0 —store de nightshift compartido y workdir no— el
        benchmark le daría ventaja a nightshift por construcción.
        """
        import tempfile

        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        registro = Path(tmp.name) / "registro.jsonl"
        agente = ("/bin/sh -c "
                  "'echo \"$NIGHTSHIFT_BENCH_ROW|$NIGHTSHIFT_BENCH_TASK|"
                  "$NIGHTSHIFT_BENCH_STORE|$NIGHTSHIFT_BENCH_WORKDIR\" >> %s'" % registro)
        code, _, err = self.run_cli(
            ["bench", "run", "--fixture", str(FIXTURES / "fixture-a.json"),
             "--prereg", str(self.prereg_congelado()), "--agent", agente,
             "--rows", "S1", "--repeats", "2", "--timeout", "60"])
        self.assertIn(code, (0, 1), err)

        filas = [l.split("|") for l in registro.read_text(encoding="utf-8").splitlines() if l]
        self.assertEqual(len(filas), 8, "1 fila × 2 repeticiones × 4 tareas")
        por_repeticion = {}
        for _, tarea, store, workdir in filas:
            por_repeticion.setdefault(store, set()).add(workdir)

        self.assertEqual(len(por_repeticion), 2, "una memoria por repetición")
        for store, workdirs in por_repeticion.items():
            self.assertEqual(len(workdirs), 1,
                             "las 4 tareas de una repetición comparten ruta de trabajo")
        rutas = {w for ws in por_repeticion.values() for w in ws}
        self.assertEqual(len(rutas), 2, "y cada repetición tiene la suya")

    def test_el_contenido_del_repo_se_resetea_entre_tareas(self):
        """La ruta se mantiene, el contenido no: si no, la tarea 2 encuentra el fix hecho."""
        import tempfile

        fixture = bench.load_fixture(FIXTURES / "fixture-a.json")
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        destino = Path(tmp.name) / "trabajo"
        primero = Path(bench.prepare_workdir(fixture, destino))
        (primero / "state").mkdir(exist_ok=True)
        (primero / "state" / "t1.fixed").write_text("listo", encoding="utf-8")
        segundo = Path(bench.prepare_workdir(fixture, destino))
        self.assertEqual(primero, segundo, "misma ruta")
        self.assertFalse((segundo / "state" / "t1.fixed").exists(), "contenido reseteado")

    def test_el_fingerprint_del_repo_no_depende_de_la_ruta(self):
        """Sin remote, el fingerprint sale de la ruta y dos repeticiones son dos repos."""
        import tempfile

        from nightshift import context

        fixture = bench.load_fixture(ROOT / "bench" / "fixtures" / "familia-a" /
                                     "fixture.json")
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        uno = bench.prepare_workdir(fixture, Path(tmp.name) / "S1-c1")
        dos = bench.prepare_workdir(fixture, Path(tmp.name) / "S1-c2")
        self.assertEqual(context.repo_fingerprint(uno), context.repo_fingerprint(dos))
        self.assertIsNotNone(context.base_commit(uno),
                             "sin commit no hay base_commit, y sin eso no hay verify")

    def prereg_congelado(self):
        import tempfile

        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        path = Path(tmp.name) / "prereg.md"
        path.write_text(CONGELADO, encoding="utf-8")
        return path

    def test_report_sin_corridas_lo_dice(self):
        code, _, err = self.run_cli(["bench", "report"])
        self.assertEqual(code, 1)
        self.assertIn("no hay corridas registradas", err)


if __name__ == "__main__":
    unittest.main()
