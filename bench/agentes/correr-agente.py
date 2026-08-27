#!/usr/bin/env python3
"""Adaptador del agente para una celda del benchmark (PREREG §2).

Lanza Claude Code sobre la tarea de la celda y emite las métricas que el runner sabe
leer. Es la pieza entre "el runner sabe qué correr" y "algo corre".

**Se niega a correr sin las constantes pre-registradas**, por el mismo motivo que
`nightshift bench run` se niega con el pre-registro abierto: el modelo, el límite de tool
calls y el protocolo de reset son decisiones que se congelan *antes*, no valores que un
script elige por su cuenta. Cada una es un `TODO(Matias)` de `bench/PREREG.md`.

Las filas (PREREG §2):

- `S0` — Claude Code con Auto Memory y Auto Dream encendidos. **Sin nightshift.**
- `S1` — lo mismo más nightshift cargado como plugin, con su store por **(fila,
  repetición)**: dentro de una repetición la memoria se acumula tarea a tarea, que es lo
  único que hace que la fase de aprendizaje le enseñe algo a la de medición.
- `S2` — es de M5, y M5 está bloqueado hasta el veredicto de M4. Se rechaza.

Verificado contra el CLI el 2026-08-26:

- `--output-format stream-json` emite un evento `assistant` por mensaje, y los bloques
  `tool_use` de su contenido son las tool calls. Contarlas ahí es la métrica secundaria
  de PREREG §3; `num_turns` del resultado **no** es lo mismo y se reporta aparte.
- Esta versión del CLI **no expone `--max-turns`**, así que el límite de tool calls no se
  puede imponer: se mide y se reporta si se excedió. Un límite que se dice y no se aplica
  hay que decirlo, no suponerlo aplicado.
"""

import json
import os
import pathlib
import subprocess
import sys
import uuid
from pathlib import Path

FILAS = ("S0", "S1")
RAIZ_NIGHTSHIFT = Path(__file__).resolve().parent.parent.parent

CONSTANTES = {
    "NIGHTSHIFT_BENCH_MODEL": "el modelo exacto y su versión (PREREG §2)",
    "NIGHTSHIFT_BENCH_TOOL_LIMIT": "el límite de tool calls por tarea (PREREG §2)",
    "NIGHTSHIFT_BENCH_RESET": "el comando de reset entre corridas (PREREG §5). Si el "
                              "protocolo dice que no hace falta resetear nada, poné `true`",
}


def faltantes():
    return {clave: motivo for clave, motivo in CONSTANTES.items() if not os.environ.get(clave)}


def contar_tool_calls(linea, contador):
    """Suma los bloques `tool_use` de un evento del stream. Devuelve el evento `result`."""
    linea = linea.strip()
    if not linea.startswith("{"):
        return None
    try:
        evento = json.loads(linea)
    except ValueError:
        return None
    if evento.get("type") == "assistant":
        for bloque in evento.get("message", {}).get("content") or []:
            if bloque.get("type") == "tool_use":
                contador.append(bloque.get("name") or "?")
    return evento if evento.get("type") == "result" else None


def main(argv):
    if len(argv) < 2:
        print("uso: correr-agente.py <fila> <prompt>", file=sys.stderr)
        return 2
    fila, prompt = argv[0], " ".join(argv[1:])

    if fila == "S2":
        print("la fila S2 (verificados) es de M5, y M5 está bloqueado hasta que M4 dé "
              "veredicto", file=sys.stderr)
        return 3
    if fila not in FILAS:
        print("fila desconocida: %s" % fila, file=sys.stderr)
        return 2

    falta = faltantes()
    if falta:
        print("el adaptador no corre sin las constantes pre-registradas:", file=sys.stderr)
        for clave, motivo in sorted(falta.items()):
            print("  %s — %s" % (clave, motivo), file=sys.stderr)
        print(file=sys.stderr)
        print("Son TODO(Matias) de bench/PREREG.md. Un script que las elige por su cuenta",
              file=sys.stderr)
        print("está fijando la configuración del experimento después de escribirlo.",
              file=sys.stderr)
        return 3

    if os.environ.get("NIGHTSHIFT_BENCH_UNATTENDED") != "1":
        print("una corrida del benchmark no puede parar a pedir permisos: exportá "
              "NIGHTSHIFT_BENCH_UNATTENDED=1 para aceptar que el agente corre sin "
              "confirmaciones dentro de la copia desechable de la celda.", file=sys.stderr)
        return 3

    trabajo = Path(os.environ.get("NIGHTSHIFT_BENCH_WORKDIR", os.getcwd()))
    entorno = dict(os.environ)
    sesion = str(uuid.uuid4())

    comando = ["claude", "-p", prompt,
               "--output-format", "stream-json", "--verbose",
               "--model", entorno["NIGHTSHIFT_BENCH_MODEL"],
               "--session-id", sesion,
               "--permission-mode", "bypassPermissions",
               "--allow-dangerously-skip-permissions"]

    if fila == "S1":
        # nightshift cargado como plugin. El store viene del runner y vive por
        # **(fila, repetición)**, no por celda: dentro de una repetición la memoria se
        # acumula tarea a tarea, que es lo único que hace que la fase de aprendizaje le
        # enseñe algo a la de medición. Un store por celda mediría cero transferencia
        # por construcción.
        store = pathlib.Path(entorno.get("NIGHTSHIFT_BENCH_STORE") or (trabajo / ".store"))
        store.mkdir(parents=True, exist_ok=True)
        entorno["NIGHTSHIFT_HOME"] = str(store)
        comando += ["--plugin-dir", str(RAIZ_NIGHTSHIFT)]
        subprocess.run([str(RAIZ_NIGHTSHIFT / "bin" / "nightshift"), "init"],
                       env=entorno, capture_output=True, text=True, timeout=60)
        (store / "sesion.txt").write_text(sesion + "\n", encoding="utf-8")
    else:
        # S0 es el baseline: Auto Memory y Auto Dream encendidos, y nightshift ausente.
        entorno.pop("NIGHTSHIFT_HOME", None)

    reset = entorno["NIGHTSHIFT_BENCH_RESET"]
    resultado_reset = subprocess.run(reset, shell=True, cwd=str(trabajo), env=entorno,
                                     capture_output=True, text=True, timeout=300)
    if resultado_reset.returncode != 0:
        print("el reset entre corridas falló: %s" % resultado_reset.stderr.strip()[:200],
              file=sys.stderr)
        return 1

    contador = []
    resultado = None
    proceso = subprocess.Popen(comando, cwd=str(trabajo), env=entorno, text=True,
                               stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    for linea in proceso.stdout:
        evento = contar_tool_calls(linea, contador)
        if evento is not None:
            resultado = evento
    proceso.wait()

    # ¿La fila S1 recibió memoria? Es un hecho **operativo**, no un resultado: si el
    # tratamiento no se aplicó, la comparación no mide nada, y eso hay que poder verlo
    # sin mirar quién resolvió. La familia C con `cross_repo` apagado es exactamente ese
    # caso: las celdas terminan bien y no reciben nada.
    inyectadas = None
    if fila == "S1":
        inyectadas = 0
        try:
            import sqlite3

            db = store / "trajectories.sqlite3"
            if db.is_file():
                conexion = sqlite3.connect(str(db))
                inyectadas = conexion.execute(
                    "SELECT COUNT(*) FROM injections WHERE session_id = ?",
                    (sesion,)).fetchone()[0]
                conexion.close()
        except Exception:
            inyectadas = None

    limite = int(entorno["NIGHTSHIFT_BENCH_TOOL_LIMIT"])
    metricas = {
        "injections": inyectadas,
        "tool_calls": len(contador),
        "num_turns": (resultado or {}).get("num_turns"),
        "session_id": sesion,
        "row": fila,
        "cost_usd": (resultado or {}).get("total_cost_usd"),
        "tool_limit": limite,
        # El CLI no expone `--max-turns`: el límite se mide, no se impone.
        "tool_limit_exceeded": len(contador) > limite,
        "agent_exit": proceso.returncode,
    }
    print("NIGHTSHIFT_BENCH %s" % json.dumps(metricas, ensure_ascii=False))
    return proceso.returncode


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
