"""H23 — ¿La escena física transfiere donde el diagrama no?"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _marco import PASS, FAIL, BLOCKED, StoreDesechable, correr_solo

IDEA = 'idear'
HIPOTESIS = 'La escena fisica transfiere a un sintoma que no se vio, y el diagrama no.'

# El corpus del brazo físico, si alguien ya lo corrió: `experimentos/14`.
SALIDA = "experimentos/salidas/14-fisica.json"

# El conjunto retenido que haría admisible el número. NO es el de `cbbd7ff0`: ése se gastó.
RETENIDO = "experimentos/retenido/"


def correr():
    """Esta hipótesis está **BLOCKED a propósito**, y el motivo es la mitad del valor de
    este archivo.

    H17 midió el brazo Mermaid contra los tres síntomas retenidos de `cbbd7ff0`. Ese
    conjunto **ya se gastó**: se usó para diagnosticar (`09`), para comparar brazos (`07`)
    y para escribir dos reglas del prompt de consolidación. El prompt de la escena física
    lo escribió alguien que había leído esos tres síntomas el mismo día.

    Medir el brazo nuevo contra ese conjunto daría un número, y el número no valdría nada:
    es entrenar contra el test. `doc/HANDOFF.md` §4-ter lo nombra como la primera cosa que
    no hay que hacer, y ADR-007 se aceptó con esa condición escrita.

    Lo que falta no es código. Es material, y lo escribe una persona que sólo vio las
    conjeturas: el protocolo está en `experimentos/retenido/README.md`.
    """
    from pathlib import Path
    raiz = Path(__file__).resolve().parent.parent.parent

    faltan = []
    if not (raiz / SALIDA).is_file():
        faltan.append("la salida del brazo fisico: `python3 experimentos/"
                      "14-la-escena-antes-del-diagrama.py` (cuesta 2 llamadas al modelo)")
    pendientes = sorted((raiz / RETENIDO).glob("PENDIENTE-*.md"))
    sin_gastar = sorted(p.name for p in (raiz / RETENIDO).glob("*.md")
                        if not p.name.startswith(("PENDIENTE-", "README")))
    if not sin_gastar:
        faltan.append("un conjunto retenido NUEVO, escrito por alguien que solo vio las\n"
                      "     conjeturas. El de `cbbd7ff0` esta gastado y no sirve: medir\n"
                      "     contra el seria entrenar contra el test.\n"
                      "     Hay %d pendiente(s) sin llenar: %s"
                      % (len(pendientes), ", ".join(p.name for p in pendientes) or "—"))

    if faltan:
        return BLOCKED, ("no se puede comprobar todavia, y no por codigo faltante:\n"
                         + "\n".join("  - %s" % f for f in faltan)
                         + "\n\nMientras tanto H17 sigue en FAIL y ese veredicto NO se\n"
                           "toca: es sobre el brazo Mermaid, que si se midio. Convertir un\n"
                           "FAIL en BLOCKED cambiando el instrumento seria lavar un\n"
                           "resultado, que es peor que tenerlo en contra.")

    return BLOCKED, ("el material existe: falta escribir la comparacion contra el retenido\n"
                     "nuevo, con `camino_real.medir` y el control negativo, igual que H17.")


if __name__ == "__main__":
    sys.exit(correr_solo(sys.modules[__name__]))
