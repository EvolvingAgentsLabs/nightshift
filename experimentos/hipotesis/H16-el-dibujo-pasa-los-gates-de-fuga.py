"""H16 — La ideación y el diagrama pasan los mismos gates que el resto."""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _marco import PASS, FAIL, BLOCKED, StoreDesechable, correr_solo

IDEA = 'idear'
HIPOTESIS = 'La ideación y el diagrama pasan los mismos gates que el resto.'

def correr():
    from nightshift import config, dream, redact
    red = redact.Redactor(identifiers=[], deny_paths=config.DEFAULT_DENY_PATHS, home_dir=None)
    base = {"pattern": "Una etapa valida la forma del registro y nunca su contenido."}
    casos = {
        "ruta en la ideacion": (base, {"ideation": "el dato entra por /Users/x/proj/src"}),
        "ruta en el diagrama": (dict(base, diagram="flowchart LR\n  A[/Users/x/src] --> B"), {}),
        "ruta en una proyeccion": (dict(base,
                                        projected_signals=["falla al leer ~/.ssh/id_rsa"]), {}),
    }
    sin_detectar = []
    for nombre, (datos, extra) in casos.items():
        _, _, _, problemas = dream.validate(datos, redactor=red, home_dir=None, **extra)
        if not problemas:
            sin_detectar.append(nombre)
    if sin_detectar:
        return FAIL, "fugas que no se detectaron: %s" % sin_detectar
    return PASS, ("3 fugas detectadas. Ideacion, diagrama y proyecciones son texto de\n"
                  "modelo y se persisten: una fuga en cualquiera voltea la consolidacion\n"
                  "entera, igual que en el patron.")

if __name__ == "__main__":
    sys.exit(correr_solo(sys.modules[__name__]))
