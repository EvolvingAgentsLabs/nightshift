"""El techo a escala: seis ideaciones diseñadas a mano, compitiendo en un solo store.

El `08` midió el techo de la cadena con **una** abstracción escrita a mano: los tres
síntomas enganchan, ningún ajeno, y lo que falta está arriba, en la consolidación. Pero una
sesión real no encuentra una memoria sola: encuentra un store, y el `13` midió que la
discriminación se degrada cuando el store crece. Este experimento junta las dos preguntas:

> Con seis ideaciones escritas como la spec quiere —mecanismos distintos, señales con las
> palabras de quien sufre, escena y logograma que pasan sus gates— ¿cada paráfrasis
> encuentra **su** caso entre seis, y ningún prompt ajeno engancha ninguno?

Los casos están en `casos_de_ideacion.py`, diseñados primero y validados contra los gates
reales (`tests/test_casos_de_ideacion.py` lo fija en `make check`). La medición va por el
camino real: candidatas montadas con `promote_to_candidate`, `retrieve.candidates`,
`retrieve.render`, la compuerta del clasificador. No llama a ningún modelo: es gratis.

**Lo que este número ES:** el techo. Todo lo escribió la misma mano —casos, señales y
paráfrasis— así que esto mide lo mejor que la cadena puede dar con material ideal, y separa
"el instrumento no puede" de "el material no alcanza".

**Lo que NO es:** transferencia, ni evidencia de que la memoria sirva. Eso necesita un
conjunto retenido escrito por otra persona (`retenido/README.md`) y volumen real.

El veredicto automatizable vive en `hipotesis/H24`; esto imprime la matriz entera para
mirarla.
"""

import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ))
sys.path.insert(0, str(RAIZ / "experimentos"))

import casos_de_ideacion                                    # noqa: E402


def main():
    r = casos_de_ideacion.medir_a_escala()
    detalle, ajenos = r["detalle"], r["ajenos"]

    print("seis casos de ideación diseñados a mano, montados juntos en un store")
    print("desechable. Medido por el camino real; el store real NO se toca.")
    print()
    print("%-24s %-10s %-9s %-8s %-6s" % ("caso", "clasifica", "engancha", "elegida",
                                          "llega"))
    print("-" * 62)
    for d in detalle:
        print("%-24s %-10s %-9s %-8s %-6s" % (
            d["slug"], d["clasifica"],
            "SI" if d["propia_engancha"] else "no",
            "SI" if d["elegida"] else "no",
            "SI" if d["llega"] else "no"))
        if d["cruzadas"]:
            print("      también enganchó: %s" % ", ".join(
                "%s (%s)" % (s, d["motivos"].get(s, "?")) for s in d["cruzadas"]))
        if d["arriba_del_propio"]:
            print("      y ARRIBA del propio quedaron: %s"
                  % ", ".join(d["arriba_del_propio"]))
    print("-" * 62)

    propias = sum(d["propia_engancha"] for d in detalle)
    elegidas = sum(d["elegida"] for d in detalle)
    llegan = sum(d["llega"] for d in detalle)
    con_cruces = sum(bool(d["cruzadas"]) for d in detalle)
    print("%-40s %d de %d" % ("la propia engancha", propias, len(detalle)))
    print("%-40s %d de %d" % ("la propia queda entre las elegidas", elegidas,
                              len(detalle)))
    print("%-40s %d de %d   ← la compuerta del clasificador" % (
        "LLEGA al agente en una sesión real", llegan, len(detalle)))
    print()

    enganches_ajenos = [a for a in ajenos if a["engancha"]]
    print("control negativo (%d prompts ajenos): %d enganchan"
          % (len(ajenos), len(enganches_ajenos)))
    for a in enganches_ajenos:
        print("  `%s` → %s" % (a["prompt"][:50], ", ".join(a["engancha"])))
    print()

    if con_cruces:
        print("Y el dato para la decisión del piso: %d de %d paráfrasis enganchan además"
              % (con_cruces, len(detalle)))
        print("casos ajenos — la correcta llega igual, pero comparte el bloque con casos")
        print("que no hablan del problema. Es la degradación que el `13` midió sobre el")
        print("store real, reproducida sobre material diseñado para ser separable.")
        print()

    print("Todo lo de arriba lo escribió la misma mano. Es un TECHO, no transferencia:")
    print("dice qué puede dar la cadena con material ideal, nunca que la memoria sirva.")


if __name__ == "__main__":
    main()
