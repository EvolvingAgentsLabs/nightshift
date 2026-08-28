"""H04 — La cadena tiene eslabones explícitos: qué corrección arregló qué error."""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _marco import PASS, FAIL, BLOCKED, StoreDesechable, correr_solo

IDEA = 'CTE'
HIPOTESIS = 'La cadena tiene eslabones explícitos: qué corrección arregló qué error.'

def correr():
    with StoreDesechable() as d:
        columnas = {f["name"] for f in d.conn.execute("PRAGMA table_info(steps)")}
    enlaces = columnas & {"corrects_step", "caused_by", "parent_idx"}
    if enlaces:
        return PASS, "hay columnas de enlace: %s" % sorted(enlaces)
    return FAIL, ("los pasos son una lista plana con dos banderas (`decisive`,\n"
                  "`contradicted`). La cadena `hipotesis -> comando -> error ->\n"
                  "correccion -> senal decisiva -> fix` esta afirmada en el README y en la\n"
                  "spec y NO es una estructura de datos: esta implicita en el orden, que es\n"
                  "la forma mas debil de tenerla. `why` no puede decir que correccion\n"
                  "arreglo que error.\n"
                  "Es G1.2 del plan, fuera de alcance hasta tener un sintoma medido que lo\n"
                  "pida.")

if __name__ == "__main__":
    sys.exit(correr_solo(sys.modules[__name__]))
