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
    # El diagrama sólo existe en el brazo `mermaid` (con el default en `fisica` se
    # descarta antes de mirarlo, 0.3.10); la escena y el logograma, sólo en `fisica`.
    # Cada fuga se ejercita en el brazo donde ese campo es real.
    casos = {
        "ruta en la ideacion": (base, {"ideation": "el dato entra por /Users/x/proj/src"},
                                "fisica"),
        "ruta en el diagrama": (dict(base, diagram="flowchart LR\n  A[/Users/x/src] --> B"),
                                {}, "mermaid"),
        "ruta en una proyeccion": (dict(base,
                                        projected_signals=["falla al leer ~/.ssh/id_rsa"]),
                                   {}, "fisica"),
        "ruta en la escena": (dict(base, physical_scene=(
            "Una cinta transportadora lleva cajas selladas hasta una balanza que decide "
            "si cada una sigue viaje y la balanza pesa la caja entera sin abrirla, pero "
            "el manual del operario quedo guardado en /Users/x/manual y nadie lo lee."),
            logogram="caja sellada vacia"), {}, "fisica"),
    }
    sin_detectar = []
    for nombre, (datos, extra, modo) in casos.items():
        _, _, _, problemas = dream.validate(datos, redactor=red, home_dir=None,
                                            modo=modo, **extra)
        if not problemas:
            sin_detectar.append(nombre)
    if sin_detectar:
        return FAIL, "fugas que no se detectaron: %s" % sin_detectar
    return PASS, ("4 fugas detectadas, cada una en el brazo donde su campo existe.\n"
                  "Ideacion, diagrama, proyecciones y escena son texto de modelo y se\n"
                  "persisten: una fuga en cualquiera voltea la consolidacion entera,\n"
                  "igual que en el patron.")

if __name__ == "__main__":
    sys.exit(correr_solo(sys.modules[__name__]))
