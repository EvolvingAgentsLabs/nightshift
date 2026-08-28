"""El techo del oráculo: ¿el que falla es el código o el prompt? (diagnóstico de H17)

H17 falla: contra tres síntomas retenidos que ninguno de los dos brazos vio, el ideado
engancha uno más que el control y lo paga con un prompt ajeno. Eso es un resultado, pero
**no dice dónde está el problema**. Hay dos culpables posibles y la diferencia decide qué
se arregla:

1. **La máquina no puede.** Aunque la consolidación escribiera la abstracción perfecta,
   la cadena —índice, `_enganche`, ranking, inyección— no la transporta hasta el bloque
   que ve el agente. Entonces se arregla **código**.
2. **La máquina puede y el modelo no escribió eso.** La cadena transporta cualquier
   abstracción bien escrita; la que produjo `dream.build_prompt` no lo estaba. Entonces
   se arregla el **prompt** (y, si hace falta, el harness que lo corre).

Este archivo separa las dos con un tercer brazo, el **oráculo**: la abstracción que se
esperaba, escrita a mano en esta sesión, y metida por el camino real —`promote_to_candidate`
sobre un store desechable, `retrieve.candidates`, `retrieve.render`— para ver si "así
funciona todo".

**Qué NO es esto, y hay que decirlo antes que nada.** El oráculo se escribió **con el
conjunto retenido a la vista**. Por lo tanto:

- No es evidencia de nada, y en particular **no sostiene ADR-004**. Un brazo que conoce la
  respuesta gana por construcción.
- **No convierte H17 en `PASS`.** H17 mide brazos que no vieron el retenido; el oráculo lo
  vio, así que no califica como brazo. Lo que sí cambió de H17 es su *instrumento*, y por
  otro motivo: ver abajo.
- Es un **techo**: una cota superior de lo que la cadena puede transportar. Sirve por lo
  que descarta, no por lo que gana.

**Por qué el techo igual dice algo.** Alcanzar 3 de 3 en el retenido es trivial cuando se
conoce el retenido. Lo que no es trivial es alcanzarlo **sin** enganchar el control
negativo: sensibilidad y especificidad al mismo tiempo. Si ninguna redacción logra las
dos, el matcher léxico no tiene resolución para separar dos problemas que comparten
sustantivo, y eso ningún prompt lo arregla.

    python3 experimentos/08-el-techo-del-oraculo.py

No toca el store real: los brazos se montan en un `HOME` temporal. Del store real sólo
**lee** la candidata `cbbd7ff0`, que es el brazo ideado de verdad.

**Lo primero que encontró, y ya está corregido.** El 07 y H17 medían el enganche contra un
bolsón de frases `signals + pattern + decisive_signal`; la cadena real nunca matchea contra
`pattern` y sí matchea contra `valid_when`. El brazo de control anotaba así un enganche que
la máquina no produce. Desde el 2026-08-28 los tres miden por `camino_real.medir` y hay una
sola definición de "engancha", que es la del plugin.
"""

import json
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ))
sys.path.insert(0, str(RAIZ / "experimentos"))

import camino_real                                                  # noqa: E402

# ---------------------------------------------------------------- el material

# Los tres síntomas que una persona confirmó después (`nightshift resolve`), dichos con
# palabras humanas. Son los mismos de `07-idear-contra-no-idear.py` y de H17: cambiarlos
# acá sería mover el blanco.
RETENIDOS = [
    ("panel con denominador cero",
     "el resumen dice que esta todo bien pero no conto ninguna celda"),
    ("ensayo verde contra store vacio",
     "la corrida termina en verde y no proceso ni un solo caso"),
    ("linter con lista vacia",
     "el chequeo pasa porque su patron no encontro ningun archivo"),
]

# Control negativo. El tercero es el que el brazo ideado enganchó de más: habla de un
# linter, pero de otro problema.
AJENOS = [
    "el certificado ssl del dominio vencio y el deploy no arranca",
    "quiero agregar paginacion a la tabla de usuarios",
    "el linter se queja de un import sin usar",
]

# El brazo ORÁCULO: la respuesta esperada. Escrita a mano, en esta sesión, CON el retenido
# a la vista — por eso es un techo y no evidencia. Lo único que se le pidió es lo que se le
# pediría a una buena consolidación: nombrar el mecanismo con los sustantivos con los que
# una persona describiría el síntoma, y proyectar en ese mismo registro.
ORACULO = {
    "pattern": (
        "Una afirmación sobre los elementos de una colección se cumple sola cuando la "
        "colección quedó vacía: el chequeo pasa, el resumen dice que está todo bien, y en "
        "realidad no se contó ni un caso. El vacío se lee como éxito porque nadie afirma "
        "primero que haya algo que mirar. El fix es exigir contenido —afirmar que la "
        "colección no está vacía— antes de afirmar algo sobre sus elementos."
    ),
    "signals": [
        "Una corrida termina en verde habiendo procesado cero elementos.",
        "El resumen informa cobertura completa con el denominador en cero.",
        "Un chequeo pasa porque su patrón no encontró ningún archivo que revisar.",
    ],
    "decisive_signal": (
        "Romper el guard a propósito y pedir la lista de tests que deberían haber fallado: "
        "el único que sobra en esa lista es el del caso vacío, la única prueba que se quedó "
        "en verde sin mirar nada."
    ),
}

# Las proyecciones del oráculo: las mismas cinco conjeturas, dichas con los sustantivos del
# síntoma en vez de los del diseño. La quinta NO dice "linter" a propósito, y ése es el
# experimento: es la palabra que produjo la colisión con el prompt ajeno.
ORACULO_PROYECCIONES = [
    "Un resumen de salud informa cobertura perfecta sin haber contado ninguna celda: el "
    "denominador quedó en cero y no distingue todo bien de no hay nada.",
    "Un bloque de contexto inyectado cita cero ejemplos y pasa el chequeo porque el "
    "chequeo mira el formato y el largo, no el contenido.",
    "Una corrida de consolidación queda registrada como exitosa habiendo procesado cero "
    "trayectorias.",
    "Un ensayo end to end termina en verde contra un store recién creado: la corrida no "
    "proceso ni un solo caso.",
    "Un chequeo de invariantes pasa porque su patrón no encontró ningún archivo y su lista "
    "de archivos a revisar quedó vacía.",
]

# La misma quinta proyección, pero nombrando al linter: es la redacción real del brazo
# ideado. Se mide aparte para aislar cuánto de la colisión la carga esa sola palabra.
ORACULO_PROYECCIONES_CON_LINTER = ORACULO_PROYECCIONES[:4] + [
    "Un linter de invariantes pasa porque su patrón no encontró ningún archivo y su lista "
    "de archivos a revisar quedó vacía.",
]


# ------------------------------------------------------------------ la máquina

# La máquina de medir vive en `camino_real.py` y es una sola para el 07, el 08 y H17:
# dos definiciones de "engancha" es exactamente el error que este experimento encontró.


def medir(nombre, abstraccion, proyecciones):
    """Un brazo, de punta a punta, por el camino real."""
    r = camino_real.medir(abstraccion, proyecciones, RETENIDOS, AJENOS)
    detalle = [(d["etiqueta"] if d["clase"] == "retenido" else "AJENO: " + d["prompt"],
                "SI" if d["engancha"] else "no",
                "sí" if d["inyectada"] else "NO",
                d["motivos"])
               for d in r["detalle"] if d["clase"] == "retenido" or d["engancha"]]
    return {"nombre": nombre, "retenidos": r["retenidos"], "ajenos": r["ajenos"],
            "detalle": detalle}


def brazo_real():
    """El brazo ideado de verdad: se lee del store real, sólo lectura."""
    from nightshift import store
    conn = store.connect()
    try:
        fila = conn.execute("SELECT * FROM trajectories WHERE id LIKE 'cbbd7ff0%'").fetchone()
        if fila is None or not fila["abstraction_json"]:
            return None, None
        return (json.loads(fila["abstraction_json"]),
                [p["text"] for p in store.projections_of(conn, fila["id"])])
    finally:
        conn.close()


def main():
    control_path = RAIZ / "experimentos" / "salidas" / "07-control-observed.json"
    ideado, proyectadas = brazo_real()

    brazos = []
    if control_path.is_file():
        brazos.append(("control (observed)", json.loads(control_path.read_text("utf-8")), []))
    else:
        print("aviso: falta %s — el brazo de control no se mide" % control_path)
    if ideado is not None:
        brazos.append(("ideado (real, cbbd7ff0)", ideado, proyectadas))
    else:
        print("aviso: `cbbd7ff0` no está en este store — el brazo ideado no se mide")
    brazos.append(("ORÁCULO (techo, conoce el retenido)", ORACULO, ORACULO_PROYECCIONES))
    brazos.append(("ORÁCULO, pero diciendo `linter`", ORACULO, ORACULO_PROYECCIONES_CON_LINTER))

    print("el techo del oráculo — ¿el que falla es el código o el prompt?")
    print()
    print("%-38s %-12s %s" % ("brazo", "retenidos", "control negativo"))
    print("-" * 74)
    resultados = []
    for nombre, abstraccion, proyecciones in brazos:
        r = medir(nombre, abstraccion, proyecciones)
        resultados.append(r)
        print("%-38s %d de %-8d %d de %d" % (nombre[:38], r["retenidos"], len(RETENIDOS),
                                             r["ajenos"], len(AJENOS)))
    print("-" * 74)
    print()
    for r in resultados:
        print("· %s" % r["nombre"])
        for etiqueta, engancha, inyectada, motivos in r["detalle"]:
            print("    %-34s engancha=%-3s inyectada=%-3s %s"
                  % (etiqueta[:34], engancha, inyectada, motivos))
        print()

    techo = next(r for r in resultados if r["nombre"].startswith("ORÁCULO (techo"))
    print("=" * 74)
    if techo["retenidos"] == len(RETENIDOS) and techo["ajenos"] == 0:
        print("LA CADENA PUEDE.  Con la abstracción esperada, los tres síntomas retenidos")
        print("enganchan y ninguno de los ajenos: `candidates` los rankea por enganche y")
        print("`render` los inyecta. Entonces lo que le falta a H17 NO es código de")
        print("retrieval: es que `dream.build_prompt` produzca esa abstracción. Se arregla")
        print("arriba —prompt y harness de consolidación—, no abajo.")
    elif techo["retenidos"] < len(RETENIDOS):
        print("LA CADENA NO PUEDE.  Ni siquiera con la abstracción esperada llegan los")
        print("tres. Hay un techo de código: ningún prompt lo levanta.")
    else:
        print("LA CADENA PUEDE, PERO NO DISCRIMINA.  Los tres retenidos enganchan y")
        print("también engancha un ajeno: el matcher no separa dos problemas que comparten")
        print("sustantivo. Eso es código, no prompt.")
    print()
    print("Y esto sigue sin ser evidencia: el oráculo se escribió con el retenido a la")
    print("vista. Es un techo — dice qué se puede arreglar dónde, no que idear sirva.")
    print("El oráculo no es un brazo de H17: vio el retenido, y por eso no puntúa ahí.")
    print("=" * 74)


if __name__ == "__main__":
    main()
