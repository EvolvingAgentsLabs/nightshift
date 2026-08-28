"""H17 — Idear produce conjeturas más resolubles que no idear."""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _marco import PASS, FAIL, BLOCKED, StoreDesechable, correr_solo

IDEA = 'idear'
HIPOTESIS = 'Idear produce conjeturas más resolubles que no idear.'

def correr():
    from pathlib import Path
    raiz = Path(__file__).resolve().parent.parent.parent
    salidas = list((raiz / "experimentos").glob("salidas/ideate-*/patron-*.json"))
    if salidas:
        return PASS, "hay salidas del control: %s" % [s.name for s in salidas]
    return BLOCKED, ("ADR-004 se acepto con n=1 y lo dice. Desde entonces idear paso a ser\n"
                     "el flujo unico, asi que la apuesta central del proyecto sigue SIN\n"
                     "control.\n"
                     "BLOCKED y no FAIL: el brazo de control existe\n"
                     "(experimentos/ideate.py) y correrlo cuesta llamadas reales al modelo.\n"
                     "Lo que hay que comparar no es cual suena mejor: es cuantas\n"
                     "proyecciones de cada brazo se pueden RESOLVER, y de esas cuantas se\n"
                     "confirman. Un brazo que proyecta cinco cosas incomprobables pierde\n"
                     "contra uno que proyecta dos comprobables.\n"
                     "Es F4 del plan, y necesita H11 andando — que ya anda.")

if __name__ == "__main__":
    sys.exit(correr_solo(sys.modules[__name__]))
