"""Consolida el mismo corpus dos veces: prompt actual vs prompt con un bloque `ideate`.

La única variable es el prompt. Las trayectorias son las mismas, el modelo es el mismo y
el corpus se arma con `dream.build_prompt`, que es el que usa el plugin de verdad — así
el brazo de control **es** el comportamiento actual, no una reconstrucción parecida.

El bloque `ideate` pide lo que pidió Matías: idear antes de razonar, en imágenes. No como
adorno — la hipótesis es que **el dibujo de un mecanismo es invariante entre síntomas de
un modo que la prosa no lo es**, y que abstraer desde el dibujo produce un patrón que
transfiere a un síntoma que no se vio.

Esto vive en `experimentos/` y no en `nightshift/` a propósito. Si resulta que sirve,
entra al plugin por el camino normal.
"""

import argparse
import json
import subprocess
import sys

IDEATE = """Antes de responder, IDEÁ. No razones todavía: dibujá.

Describí el mecanismo que está fallando como si tuvieras que dibujarlo para alguien que
no leyó el código — una escena, un diagrama, una animación de dos o tres cuadros. Qué
objeto entra, qué forma tiene, por dónde pasa, en qué se convierte, dónde deja de
coincidir con lo que el resto del sistema espera.

Reglas de la ideación:

- Dibujá el MECANISMO, no el síntoma. El síntoma es dónde se vio el humo; el mecanismo es
  qué se está quemando. Dos fallas con el mismo dibujo son la misma falla.
- Usá el vocabulario del dibujo: formas, recorridos, antes y después, qué se conserva y
  qué se pierde en cada paso. Si algo cambia de forma sin que nadie lo mire, ese es el
  cuadro que importa.
- Si el mecanismo se parece al de otro dominio —una señal que atraviesa un filtro y sale
  deformada, dos llaves que abren la misma cerradura, un fluido que se escapa por una
  junta— decilo. Esa analogía es el puente, no una decoración.
- Tres a seis oraciones. Es un boceto, no un tratado.

Escribí la ideación primero, en prosa, entre las marcas <ideacion> y </ideacion>.
Después, y sólo después, el JSON que se te pide abajo.

---

"""


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
    corpus = dream.build_prompt(conn, grupo)
    print("  corpus: %d trayectoria(s) del mismo tipo de tarea" % len(grupo))

    import shutil
    comando = [shutil.which("claude"), "-p", "--output-format", "json",
               "--model", args.modelo]

    for brazo, prompt in (("control", corpus), ("ideado", IDEATE + corpus)):
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
