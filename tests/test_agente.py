"""El adaptador del agente: que se niegue, y que cuente bien.

Ningún test de acá llama a la API. El contador se prueba contra un stream grabado de una
corrida real (una tool call, dos turnos), y las negativas se prueban sin ejecutar nada.
"""

import json
import os
import subprocess
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
ADAPTADOR = ROOT / "bench" / "agentes" / "correr-agente.py"

# Grabado de `claude -p --output-format stream-json` el 2026-08-26, recortado.
STREAM = [
    '{"type":"system","subtype":"init","session_id":"s"}',
    '{"type":"assistant","message":{"content":[{"type":"text","text":"voy a leerlo"}]}}',
    '{"type":"assistant","message":{"content":[{"type":"tool_use","name":"Read",'
    '"input":{"file_path":"a.txt"}}]}}',
    '{"type":"user","message":{"content":[{"type":"tool_result","content":"hola"}]}}',
    '{"type":"assistant","message":{"content":[{"type":"text","text":"dice hola"}]}}',
    '{"type":"result","num_turns":2,"total_cost_usd":0.01,"is_error":false}',
]


def cargar():
    import importlib.util

    spec = importlib.util.spec_from_file_location("correr_agente", ADAPTADOR)
    modulo = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(modulo)
    return modulo


class ContadorTest(unittest.TestCase):
    def test_cuenta_las_tool_calls_del_stream(self):
        modulo = cargar()
        contador, resultado = [], None
        for linea in STREAM:
            evento = modulo.contar_tool_calls(linea, contador)
            if evento is not None:
                resultado = evento
        self.assertEqual(contador, ["Read"])
        self.assertEqual(resultado["num_turns"], 2)

    def test_num_turns_no_es_tool_calls(self):
        """Hacer pasar uno por el otro sería inventar la métrica secundaria de PREREG."""
        modulo = cargar()
        contador, resultado = [], None
        for linea in STREAM:
            evento = modulo.contar_tool_calls(linea, contador)
            if evento is not None:
                resultado = evento
        self.assertNotEqual(len(contador), resultado["num_turns"])

    def test_la_basura_del_stream_no_lo_rompe(self):
        modulo = cargar()
        contador = []
        for linea in ("", "no es json", "{roto", "[]", '{"type":"otro"}'):
            self.assertIsNone(modulo.contar_tool_calls(linea, contador))
        self.assertEqual(contador, [])


class NegativasTest(unittest.TestCase):
    def correr(self, fila="S0", **entorno):
        env = {k: v for k, v in os.environ.items()
               if not k.startswith("NIGHTSHIFT_BENCH_")}
        env.update(entorno)
        return subprocess.run([sys.executable, str(ADAPTADOR), fila, "hola"],
                              capture_output=True, text=True, timeout=60, env=env)

    def test_sin_las_constantes_pre_registradas_no_corre(self):
        salida = self.correr()
        self.assertEqual(salida.returncode, 3)
        for clave in ("NIGHTSHIFT_BENCH_MODEL", "NIGHTSHIFT_BENCH_TOOL_LIMIT",
                      "NIGHTSHIFT_BENCH_RESET"):
            self.assertIn(clave, salida.stderr)
        self.assertIn("TODO(Matias)", salida.stderr)

    def test_la_fila_S2_se_rechaza(self):
        salida = self.correr(fila="S2")
        self.assertEqual(salida.returncode, 3)
        self.assertIn("M5", salida.stderr)

    def test_no_corre_sin_aceptar_que_es_desatendido(self):
        salida = self.correr(NIGHTSHIFT_BENCH_MODEL="x", NIGHTSHIFT_BENCH_TOOL_LIMIT="40",
                             NIGHTSHIFT_BENCH_RESET="true")
        self.assertEqual(salida.returncode, 3)
        self.assertIn("UNATTENDED", salida.stderr)


class DocumentacionTest(unittest.TestCase):
    def test_el_readme_dice_que_el_limite_no_se_impone(self):
        texto = (ROOT / "bench" / "agentes" / "README.md").read_text(encoding="utf-8")
        self.assertIn("no expone `--max-turns`", texto)
        self.assertIn("se mide y se reporta", texto)


if __name__ == "__main__":
    unittest.main()
