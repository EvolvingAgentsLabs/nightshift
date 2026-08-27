"""Consolida el mismo corpus dos veces: prompt actual vs prompt con un bloque `ideate`.

La única variable es el prompt. Las trayectorias son las mismas, el modelo es el mismo y
los dos corpus salen de `dream.build_prompt`, que es el que usa el plugin de verdad — así
el brazo ideado **es** el comportamiento actual, no una reconstrucción parecida.

El bloque `ideate` pide lo que pidió Matías: idear antes de razonar, en imágenes. No como
adorno — la hipótesis es que **el dibujo de un mecanismo es invariante entre síntomas de
un modo que la prosa no lo es**, y que abstraer desde el dibujo produce un patrón que
transfiere a un síntoma que no se vio.

**Entró al plugin.** El bloque de ideación ya no vive acá: es `dream.IDEATE_PREFIX`, y
`consolidate` lo antepone siempre (ADR-004, enmienda 0.3.7). Este script conserva una sola
cosa que el plugin ya no tiene — el **brazo de control**, `build_prompt(..., ideate=False)`
— porque sin control no se puede volver a medir la diferencia. Que el control sea
alcanzable desde acá no lo vuelve una opción del producto: en el plugin no hay ninguna
ruta que apague la ideación.
"""

import argparse
import json
import subprocess
import sys


def consolidar(comando, prompt):
    out = subprocess.run(comando, input=prompt, capture_output=True, text=True,
                         timeout=600)
    if out.returncode != 0:
        raise SystemExit("el modelo salió %d: %s" % (out.returncode, out.stderr[:300]))
    return out.stdout


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--raiz", required=True)
    ap.add_argument("--salida", required=True)
    ap.add_argument("--modelo", default="sonnet")
    args = ap.parse_args()

    sys.path.insert(0, args.raiz)
    from nightshift import dream, store

    conn = store.connect()
    grupos = dream.groups(conn, lookback_days=3650)
    if not grupos:
        raise SystemExit("no hay trayectorias cerradas que consolidar")
    grupo = max(grupos, key=len)
    # El control es el prompt **sin** idear, que en el plugin ya no es alcanzable: hay
    # que pedirlo explícitamente. El brazo ideado usa el mismo bloque que corre en
    # producción — no una copia parecida — que es la única forma de que este experimento
    # siga midiendo lo que el plugin hace.
    corpus = dream.build_prompt(conn, grupo, ideate=False)
    ideado = dream.build_prompt(conn, grupo, ideate=True)
    print("  corpus: %d trayectoria(s) del mismo tipo de tarea" % len(grupo))

    import shutil
    comando = [shutil.which("claude"), "-p", "--output-format", "json",
               "--model", args.modelo]

    for brazo, prompt in (("control", corpus), ("ideado", ideado)):
        crudo = consolidar(comando, prompt)
        # El bloque de ideación es prosa antes del JSON; `extract_json` lo saltea igual.
        ideacion = ""
        # El envoltorio del agente trae la respuesta como string JSON, así que los
        # saltos de línea llegan escapados. Sin esto la ideación se imprime con `\n`
        # literales en el medio.
        crudo = crudo.replace("\\n", "\n")
        if "<ideacion>" in crudo:
            ideacion = crudo.split("<ideacion>", 1)[1].split("</ideacion>", 1)[0].strip()
        elif "ideacion>" in crudo:                 # el modelo escapó las marcas
            ideacion = crudo.split("ideacion>", 1)[1].split("<", 1)[0].strip()
        data = dream.extract_json(crudo) or {}
        patron = (data.get("pattern") or "—").strip()

        print()
        print("  ▸ %s" % brazo.upper())
        if ideacion:
            print("    ideación:")
            for linea in _envolver(ideacion, 74):
                print("      %s" % linea)
        print("    patrón:")
        for linea in _envolver(patron, 74):
            print("      %s" % linea)
        senales = data.get("signals") or []
        if senales:
            print("    señales: %s" % "; ".join(str(s) for s in senales[:3]))

        with open("%s/patron-%s.json" % (args.salida, brazo), "w",
                  encoding="utf-8") as fh:
            json.dump({"pattern": patron, "ideacion": ideacion, "raw": data}, fh,
                      indent=2, ensure_ascii=False)

        # El preámbulo de la prueba ciega: sólo el patrón, nunca la ideación. Lo que se
        # compara es qué abstracción transfiere, no cuánto texto se inyecta.
        with open("%s/inyeccion-%s.txt" % (args.salida, brazo), "w",
                  encoding="utf-8") as fh:
            fh.write("Memoria procedimental de sesiones anteriores en este repositorio "
                     "(no verificada):\n\n%s\n\n---\n\n" % patron)
    conn.close()


def _envolver(texto, ancho):
    import textwrap
    lineas = []
    for parrafo in texto.splitlines():
        lineas += textwrap.wrap(parrafo, ancho) or [""]
    return lineas


if __name__ == "__main__":
    main()
