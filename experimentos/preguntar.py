"""Presentar lo que dream **proyectó** como opciones, y resolverlo con una persona.

Idea de Matías, del 2026-08-27, mirando cómo una sesión de agente resuelve sus propios
bloqueos: cuando no puede decidir, presenta opciones concretas con su consecuencia y sigue
con la respuesta. Eso es exactamente lo que le falta a lo que dream produce.

Hoy `projected_signals` (ADR-004) son conjeturas que nadie observó. Se inyectan con la
mitad del peso, anunciadas como tales, y **nada las resuelve nunca**: no hay camino por el
que una conjetura pase a ser otra cosa. Este experimento prueba uno — preguntar.

Tres cosas que este experimento NO hace, y son las que lo hacen honesto:

1. **No escribe en el store.** Abre la base en modo sólo lectura y el veredicto va a un
   archivo aparte. Una respuesta humana no puede cambiar el estado de una trayectoria por
   la puerta de atrás.
2. **No es `verify`.** ADR-002 define verificar como reproducir contra un gate: un
   comando, un exit code, un `run_id`. "El usuario dijo que sí" no es eso. Si esto alguna
   vez entra al plugin, entra como un tercer estado —`human_reviewed`— con menos peso que
   una reproducción y más que una conjetura. Nunca como `procedure`.
3. **No contrasta caminos.** La otra mitad de la idea —varios agentes siguiendo
   alternativas distintas y puliéndose unos contra otros antes de que la vea nadie— no
   está acá. Cuesta una consolidación por camino y necesita el veredicto de M4 antes de
   valer la pena. Lo que se prueba acá es la **forma de la pregunta**, que es lo barato.

Vive en `experimentos/` a propósito: no toca el flujo por defecto, no participa del brazo
S1 del benchmark, y no cierra ningún gate. Si resulta que sirve, entra al plugin por el
camino normal y después del veredicto de M4.

    python3 experimentos/preguntar.py                    # sobre el store real, sólo lectura
    python3 experimentos/preguntar.py --store /tmp/x     # sobre otro
    python3 experimentos/preguntar.py --dry-run          # muestra las preguntas y no pregunta
"""

import argparse
import json
import os
import sqlite3
import sys
from datetime import datetime, timezone
from pathlib import Path

# Las opciones. Son cuatro y no dos a propósito: "no la vi" y "no puede pasar" son
# respuestas distintas y confundirlas es perder la única información cara de la sesión.
# La cuarta —"no sé"— existe para que nadie tenga que mentir para seguir: una proyección
# sin veredicto es un dato, y forzar un sí/no la convertiría en ruido con forma de dato.
OPCIONES = [
    ("la vi", "La vi pasar. Es una observación, no una conjetura.",
     "sube: el mecanismo predijo algo que ocurrió"),
    ("no puede pasar", "Sé por qué no puede ocurrir en este sistema.",
     "baja: la proyección se descarta con motivo"),
    ("no la vi todavía", "No la vi, pero es plausible: no tengo cómo descartarla.",
     "queda: sigue siendo conjetura, sin cambio"),
    ("no sé", "No tengo forma de saberlo.",
     "queda, y se anota que nadie pudo decidirla"),
]


def abrir_solo_lectura(ruta: Path):
    """Sólo lectura, y a nivel de SQLite: que la promesa no dependa de mi disciplina."""
    if not ruta.is_file():
        raise SystemExit("no hay store en %s" % ruta)
    conn = sqlite3.connect("file:%s?mode=ro" % ruta, uri=True)
    conn.row_factory = sqlite3.Row
    return conn


def proyecciones(conn):
    """Cada proyección con la candidata de la que salió. Vacío si dream no proyectó."""
    columnas = {f["name"] for f in conn.execute("PRAGMA table_info(trajectories)")}
    if "projected_signals_json" not in columnas:
        return []
    filas = conn.execute(
        "SELECT id, task_type, abstraction_json, projected_signals_json, diagram"
        " FROM trajectories WHERE status IN ('candidate','procedure')"
        " AND projected_signals_json IS NOT NULL AND projected_signals_json != ''"
        " ORDER BY created_at DESC").fetchall()
    salida = []
    for fila in filas:
        try:
            senales = json.loads(fila["projected_signals_json"]) or []
            abstraccion = json.loads(fila["abstraction_json"] or "{}")
        except ValueError:
            continue
        for senal in senales:
            if isinstance(senal, str) and senal.strip():
                salida.append({"trajectory": fila["id"], "task_type": fila["task_type"],
                               "pattern": abstraccion.get("pattern") or "",
                               "diagram": fila["diagram"] or "", "projected": senal.strip()})
    return salida


def mostrar(item, indice, total):
    print()
    print("─" * 78)
    print("proyección %d de %d · de la candidata `%s` (%s)"
          % (indice, total, item["trajectory"][:8], item["task_type"]))
    print("─" * 78)
    if item["pattern"]:
        print("\npatrón consolidado (esto SÍ salió de pasos observados):")
        for linea in envolver(item["pattern"]):
            print("  %s" % linea)
    if item["diagram"]:
        print("\nel mecanismo, como lo dibujó dream:")
        for linea in item["diagram"].splitlines()[:12]:
            print("  │ %s" % linea)
    print("\nLO PROYECTADO — nadie lo observó, es una conjetura leída del dibujo:")
    for linea in envolver(item["projected"]):
        print("  » %s" % linea)
    print()
    for numero, (etiqueta, detalle, efecto) in enumerate(OPCIONES, start=1):
        print("  %d) %-18s %s" % (numero, etiqueta, detalle))
        print("     %s" % efecto)


def envolver(texto, ancho=72):
    palabras, linea, salida = texto.split(), "", []
    for palabra in palabras:
        if len(linea) + len(palabra) + 1 > ancho:
            salida.append(linea)
            linea = palabra
        else:
            linea = "%s %s" % (linea, palabra) if linea else palabra
    if linea:
        salida.append(linea)
    return salida or [""]


def preguntar(item, indice, total):
    mostrar(item, indice, total)
    while True:
        try:
            respuesta = input("\n  ¿cuál? [1-4, o `s` para saltar, `q` para cortar] ").strip().lower()
        except (EOFError, KeyboardInterrupt):
            print()
            return None
        if respuesta in ("q", "quit", "salir"):
            return None
        if respuesta in ("s", "skip", "saltar", ""):
            return "saltada"
        if respuesta in ("1", "2", "3", "4"):
            return OPCIONES[int(respuesta) - 1][0]
        print("  no entendí. 1, 2, 3, 4, `s` o `q`.")


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--store", help="directorio del store (por defecto ~/.nightshift)")
    parser.add_argument("--salida", help="dónde escribir el veredicto (JSONL)")
    parser.add_argument("--dry-run", action="store_true",
                        help="mostrar las preguntas y no preguntar nada")
    args = parser.parse_args(argv)

    raiz = Path(args.store or os.environ.get("NIGHTSHIFT_HOME")
                or (Path.home() / ".nightshift")).expanduser()
    conn = abrir_solo_lectura(raiz / "trajectories.sqlite3")
    try:
        items = proyecciones(conn)
    finally:
        conn.close()

    print("preguntar — lo proyectado, presentado como opciones (experimento)")
    print("store: %s (sólo lectura)" % raiz)
    if not items:
        print()
        print("No hay proyecciones que preguntar.")
        print("Salen de `nightshift dream`, que idea siempre (ADR-004, enmienda 0.3.7),")
        print("y sólo las tienen las trayectorias que llegaron a `candidate`.")
        return 0
    print("%d proyección(es) sin resolver, de %d candidata(s)."
          % (len(items), len({i["trajectory"] for i in items})))

    if args.dry_run:
        for numero, item in enumerate(items, start=1):
            mostrar(item, numero, len(items))
        print()
        print("(--dry-run: no se preguntó nada y no se escribió nada)")
        return 0

    veredictos = []
    for numero, item in enumerate(items, start=1):
        respuesta = preguntar(item, numero, len(items))
        if respuesta is None:
            print("\n  cortado. Lo respondido hasta acá se guarda igual.")
            break
        veredictos.append(dict(item, verdict=respuesta,
                               at=datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")))

    destino = Path(args.salida or (raiz / "veredictos-humanos.jsonl")).expanduser()
    with destino.open("a", encoding="utf-8") as fh:
        for veredicto in veredictos:
            fh.write(json.dumps(veredicto, ensure_ascii=False) + "\n")

    conteo = {}
    for veredicto in veredictos:
        conteo[veredicto["verdict"]] = conteo.get(veredicto["verdict"], 0) + 1
    print()
    print("─" * 78)
    for etiqueta, veces in sorted(conteo.items(), key=lambda kv: -kv[1]):
        print("  %-18s %d" % (etiqueta, veces))
    print("\nveredictos en: %s" % destino)
    print()
    print("Esto NO promovió nada. Ninguna trayectoria cambió de estado y el store no se")
    print("tocó: se abrió en modo sólo lectura. Verificar es reproducir contra un gate")
    print("(ADR-002) y una respuesta humana no es una reproducción — si esto entra al")
    print("plugin, entra como un estado propio con su propio peso, nunca como `procedure`.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
