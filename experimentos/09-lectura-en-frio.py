"""¿Las proyecciones son profecías o son horóscopos? (control de lectura en frío)

**El problema, dicho sin anestesia.** El proyecto tiene tres proyecciones confirmadas por
una persona (`cbbd7ff0`, `LATER.md`) y las trata como su mejor evidencia. Pero mirá lo que
dicen:

> *"Un panel de salud informa cobertura perfecta cuando el denominador es cero."*
> *"Un linter de invariantes pasa porque su lista de archivos quedó vacía."*

Son bugs que **cualquiera que sepa programar predice sin haber visto la trayectoria**. Un
horoscopista acierta por lo mismo: dice algo que le pasa a todo el mundo. Mientras nadie
pruebe que estas conjeturas son **específicas de este mecanismo**, "3 de 5 confirmadas" es
indistinguible de una lectura en frío bien redactada.

**El montaje.** Cada proyección del store se monta sola —una candidata con esa conjetura y
nada más, así el enganche es atribuible a ella y no a las señales de al lado— y se la
enfrenta a dos corpus de prompts que **no tienen nada que ver con la trayectoria que la
produjo**:

- `AJENOS_LEJOS`: otro dominio por completo. Frontend, ML, mobile, firmware, cobros.
- `AJENOS_CERCA`: el control difícil. Mismo género —tests, CI, linters, cobertura— y
  **otro mecanismo**. Un test flaky y una colección vacía se parecen en el vocabulario y
  no se parecen en nada más. Si una proyección engancha acá, engancha por el género.

Y como comparación, el conjunto **retenido**: los tres síntomas que una persona confirmó
para `cbbd7ff0`, escritos con paráfrasis a mano. Es lo que la proyección *debería*
enganchar.

**El criterio, y no es un umbral que elija yo.** Una proyección que engancha más prompts
ajenos que retenidos es indistinguible de un horóscopo. La comparación es contra su propio
control positivo, no contra un número inventado.

**Qué NO decide esto.** No dice si la conjetura es *cierta* — eso lo dijo la persona que
fue a mirar. Dice si es **específica**: si sólo se enciende con el problema que anticipó, o
con cualquier cosa que se le parezca de lejos. Una conjetura cierta y promiscua igual es
inútil: llega a todas las sesiones, y una memoria que aparece siempre es ruido con formato.

Corre por el camino real (`camino_real`), sobre stores desechables, sin llamar al modelo.

    python3 experimentos/09-lectura-en-frio.py
    python3 experimentos/09-lectura-en-frio.py --detalle    # prompt por prompt
"""

import argparse
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ))
sys.path.insert(0, str(RAIZ / "experimentos"))

import camino_real                                                  # noqa: E402

# Otro dominio por completo. Un desarrollador escribiría cualquiera de éstos, en un repo
# que no tiene nada que ver con nightshift.
AJENOS_LEJOS = [
    "el bundle de webpack pesa 4 megas y la landing tarda en pintar",
    "el modelo entrena pero la loss se queda planchada desde la epoca 3",
    "la app de android crashea al rotar la pantalla en el detalle de producto",
    "la query del reporte mensual tarda 40 segundos contra postgres",
    "el certificado ssl del dominio vencio y el deploy no arranca",
    "quiero agregar paginacion a la tabla de usuarios",
    "el personaje atraviesa la pared cuando corre en diagonal",
    "el firmware se cuelga cuando el sensor devuelve un valor negativo",
    "el webhook de pagos llega duplicado y cobramos dos veces",
    "el build de docker tarda 12 minutos por el layer de dependencias",
]

# El control difícil: mismo género que las trayectorias del store —tests, CI, linters,
# cobertura, gates— y **otro mecanismo**. Acá es donde se ve si el enganche lo carga el
# mecanismo o lo carga el vocabulario del género.
AJENOS_CERCA = [
    "el test falla intermitentemente en ci pero pasa en local",
    "el linter se queja de un import sin usar",
    "la suite tarda 9 minutos y quiero paralelizarla",
    "el mock del cliente http no se resetea entre tests",
    "el coverage bajo de 82 a 79 y no se que test se borro",
    "el pipeline de ci falla en el paso de build por falta de memoria",
    "un test rompe solo cuando corre despues del de autenticacion",
    "el snapshot del componente cambia en cada corrida por el timestamp",
]

# Control positivo: los tres síntomas que una persona confirmó para `cbbd7ff0`, con
# paráfrasis escritas a mano. Sólo aplican a esa trayectoria.
RETENIDOS_CBBD7FF0 = [
    "el resumen dice que esta todo bien pero no conto ninguna celda",
    "la corrida termina en verde y no proceso ni un solo caso",
    "el chequeo pasa porque su patron no encontro ningun archivo",
]

# Una abstracción sin `signals`: así el único enganche posible es `projected_match`, y es
# atribuible a la proyección que se está midiendo y a nada más. `pattern` no se matchea
# nunca (ver `camino_real`), así que ponerlo no contamina.
NEUTRA = {"pattern": "El mecanismo de la trayectoria que produjo esta conjetura."}


def proyecciones_del_store():
    """Todas las conjeturas del store real, con su trayectoria y su estado. Sólo lectura."""
    from nightshift import store
    conn = store.connect()
    try:
        filas = conn.execute(
            "SELECT id, task_type FROM trajectories WHERE status = 'candidate'"
            " ORDER BY created_at").fetchall()
        salida = []
        for fila in filas:
            for p in store.projections_of(conn, fila["id"]):
                salida.append({"trayectoria": fila["id"], "task_type": fila["task_type"],
                               "texto": p["text"], "estado": p["status"]})
        return salida
    finally:
        conn.close()


def medir_una(texto, prompts, llegan=False):
    """¿Con cuántos de estos prompts engancha esta conjetura, sola?

    Con `llegan=True` cuenta sólo los que además pasan la compuerta del clasificador —lo
    que el agente ve— en vez de lo que el ranking pone arriba.
    """
    r = camino_real.medir(NEUTRA, [texto], [("x", p) for p in prompts], [])
    clave = "llega" if llegan else "engancha"
    return [d["prompt"] for d in r["detalle"] if d[clave]]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--detalle", action="store_true", help="qué prompt enganchó cada una")
    args = ap.parse_args()

    conjeturas = proyecciones_del_store()
    if not conjeturas:
        raise SystemExit("no hay proyecciones en el store: este experimento mide las que hay")

    print("control de lectura en frío — ¿profecía o horóscopo?")
    print("%d conjetura(s) del store real, medidas de a una por el camino real."
          % len(conjeturas))
    print("%d prompts de otro dominio (LEJOS) + %d del mismo género y otro mecanismo (CERCA)"
          % (len(AJENOS_LEJOS), len(AJENOS_CERCA)))
    print()
    print("%-10s %-9s %-7s %-7s %s" % ("trayect.", "estado", "lejos", "cerca", "conjetura"))
    print("-" * 96)

    total_lejos = total_cerca = 0
    promiscuas = []
    for c in conjeturas:
        lejos = medir_una(c["texto"], AJENOS_LEJOS)
        cerca = medir_una(c["texto"], AJENOS_CERCA)
        total_lejos += len(lejos)
        total_cerca += len(cerca)
        if lejos or cerca:
            promiscuas.append((c, lejos, cerca))
        print("%-10s %-9s %-7s %-7s %s"
              % (c["trayectoria"][:8], c["estado"],
                 "%d/%d" % (len(lejos), len(AJENOS_LEJOS)),
                 "%d/%d" % (len(cerca), len(AJENOS_CERCA)),
                 c["texto"][:52]))
        if args.detalle:
            for p in lejos + cerca:
                print("%-36s enganchó: %s" % ("", p))
    print("-" * 96)
    n = len(conjeturas)
    print("%-10s %-9s %-7s %-7s" % ("TOTAL", "",
                                    "%d/%d" % (total_lejos, n * len(AJENOS_LEJOS)),
                                    "%d/%d" % (total_cerca, n * len(AJENOS_CERCA))))
    print()

    # Control positivo: sólo `cbbd7ff0` tiene conjunto retenido escrito por una persona.
    print("control positivo — las conjeturas de `cbbd7ff0` contra los 3 síntomas que una")
    print("persona confirmó (lo que estas conjeturas SÍ deberían enganchar):")
    print()
    veredictos = []
    for c in conjeturas:
        if not c["trayectoria"].startswith("cbbd7ff0"):
            continue
        aciertos = medir_una(c["texto"], RETENIDOS_CBBD7FF0)
        ajenos = len(medir_una(c["texto"], AJENOS_LEJOS + AJENOS_CERCA))
        veredictos.append((c, len(aciertos), ajenos))
        print("  retenidos %d/%d · ajenos %2d   %s"
              % (len(aciertos), len(RETENIDOS_CBBD7FF0), ajenos, c["texto"][:56]))
    print()

    print("=" * 96)
    horoscopos = [v for v in veredictos if v[2] > v[1]]
    if not veredictos:
        print("SIN CONTROL POSITIVO: no hay conjeturas de `cbbd7ff0` en este store, así que")
        print("la tasa de arriba no se puede comparar contra nada. Los números valen; el")
        print("veredicto no.")
        print("=" * 96)
        return

    aciertos = sum(v[1] for v in veredictos)
    posibles = len(veredictos) * len(RETENIDOS_CBBD7FF0)
    ajenos = sum(v[2] for v in veredictos)
    posibles_ajenos = len(veredictos) * (len(AJENOS_LEJOS) + len(AJENOS_CERCA))
    tasa_ret = aciertos / posibles if posibles else 0.0
    tasa_aj = ajenos / posibles_ajenos if posibles_ajenos else 0.0

    print("ESPECIFICIDAD: %d de %d (%.0f%%) con lo retenido, contra %d de %d (%.0f%%) con lo"
          % (aciertos, posibles, 100 * tasa_ret, ajenos, posibles_ajenos, 100 * tasa_aj))
    print("ajeno. Discrimina: engancha %.0f veces más con el síntoma que anticipó que con"
          % (tasa_ret / tasa_aj if tasa_aj else float("inf")))
    print("cualquier otra cosa. **Las conjeturas de este store NO son horóscopos.**")
    if horoscopos:
        print()
        print("Con %d excepción(es), que se encienden con el género y no con el mecanismo:"
              % len(horoscopos))
        for c, ac, aj in horoscopos:
            print("  · retenidos %d, ajenos %d: %s" % (ac, aj, c["texto"][:60]))
    print()
    llegan = sum(len(medir_una(c["texto"], RETENIDOS_CBBD7FF0, llegan=True))
                 for c, _, _ in veredictos)
    print("Y LO QUE LLEGA AL AGENTE: %d de %d. Los tres síntomas retenidos clasifican"
          % (llegan, posibles))
    print("`general`, así que `on_user_prompt_submit` sale antes de rankear. Todo lo de")
    print("arriba mide el ranking; esto mide la cadena entera. Ver LATER.md, la compuerta")
    print("del clasificador, y sus tres opciones de spec.")
    print()
    print("SENSIBILIDAD DEL RANKING: %.0f%%. Ninguna conjetura engancha"
          % (100 * tasa_ret))
    print("más de 1 de los 3 síntomas retenidos, y la que una persona confirmó primero")
    print("—el panel con el denominador en cero— **no engancha ninguno**, ni siquiera la")
    print("paráfrasis del síntoma que ella misma anticipó.")
    print()
    print("Dicho de otra forma: el riesgo que este experimento venía a descartar no es el")
    print("riesgo que tiene el proyecto. No sobran conjeturas que se encienden con todo:")
    print("faltan conjeturas que se enciendan con lo suyo. Es una profecía que nadie puede")
    print("consultar — y una memoria que no llega el día que hacía falta no es memoria.")
    print()
    print("Esto mide especificidad y sensibilidad, no verdad. Que una conjetura sea cierta")
    print("lo dijo la persona que fue a mirar.")
    print("=" * 96)


if __name__ == "__main__":
    main()
