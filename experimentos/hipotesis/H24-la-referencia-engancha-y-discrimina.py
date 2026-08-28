"""H24 — Con ideación escrita a mano, cada síntoma encuentra su caso y ningún ajeno engancha."""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _marco import PASS, FAIL, BLOCKED, StoreDesechable, correr_solo

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(
    os.path.abspath(__file__)))))
import casos_de_ideacion                                            # noqa: E402

IDEA = 'idear'
HIPOTESIS = ('Con ideacion escrita a mano, cada sintoma encuentra su caso entre varios '
             'y ningun ajeno engancha.')


def correr():
    """El techo del brazo físico, a escala de store y con veredicto.

    El `08` midió el techo con UNA abstracción; una sesión real encuentra un store, y el
    `13` midió que la discriminación se degrada al crecer. Acá los seis casos de
    referencia —diseñados primero, gates en `make check`— compiten en un solo store
    desechable, y se pide todo junto:

    - cada paráfrasis engancha su propio caso y lo deja entre las elegidas, y
    - ningún prompt ajeno engancha ninguno.

    **Es un techo, no transferencia**: casos, señales y paráfrasis los escribió la misma
    mano. Un PASS dice que la cadena puede separar seis mecanismos con material ideal; un
    FAIL diría que ni con material ideal puede, que es lo que el `13` insinúa del store
    real. Los cruces —una paráfrasis que engancha además un caso ajeno— no voltean el
    veredicto mientras el propio llegue, pero se reportan: son el dato de la decisión del
    piso, que es de Matías.
    """
    r = casos_de_ideacion.medir_a_escala()
    detalle, ajenos = r["detalle"], r["ajenos"]

    sin_propia = [d["slug"] for d in detalle if not d["propia_engancha"]]
    sin_eleccion = [d["slug"] for d in detalle if d["propia_engancha"]
                    and not d["elegida"]]
    enganches_ajenos = [(a["prompt"], a["engancha"]) for a in ajenos if a["engancha"]]

    if sin_propia or sin_eleccion:
        return FAIL, ("ni con material disenado la cadena separa los casos:\n"
                      "  sin enganche propio: %s\n"
                      "  enganchan pero quedan afuera de las elegidas: %s\n"
                      "Si el material ideal no alcanza, el problema no esta en la\n"
                      "consolidacion: esta en el piso, y es peor de lo que midio el 13."
                      % (", ".join(sin_propia) or "-", ", ".join(sin_eleccion) or "-"))
    if enganches_ajenos:
        return FAIL, ("un prompt ajeno engancho un caso disenado:\n"
                      + "\n".join("  `%s` -> %s" % (p[:50], ", ".join(e))
                                  for p, e in enganches_ajenos)
                      + "\nEn un corpus disenado no hay falso positivo aceptable.")

    con_cruces = [d for d in detalle if d["cruzadas"]]
    llegan = sum(d["llega"] for d in detalle)
    nota_cruces = ""
    if con_cruces:
        nota_cruces = ("\nY el dato para la decision del piso: %d de %d parafrasis\n"
                       "enganchan ademas casos ajenos (la correcta llega igual). La\n"
                       "degradacion del 13, reproducida sobre material disenado para\n"
                       "ser separable." % (len(con_cruces), len(detalle)))
    return PASS, ("las %d parafrasis enganchan su caso y lo dejan elegido; %d de %d\n"
                  "prompts ajenos enganchan algo. El techo a escala existe.\n"
                  "  Y la compuerta: LLEGAN al agente %d de %d — los %d clasifican\n"
                  "  `general` y el hook sale antes de rankear. El techo entero queda\n"
                  "  detras de la decision de spec 5.7 (LATER.md).\n"
                  "Es un TECHO: todo lo escribio la misma mano. No es transferencia\n"
                  "ni evidencia de que la memoria sirva.%s"
                  % (len(detalle), len(enganches_ajenos), len(ajenos),
                     llegan, len(detalle), len(detalle) - llegan, nota_cruces))


if __name__ == "__main__":
    sys.exit(correr_solo(sys.modules[__name__]))
