"""H15 — Un diagrama roto no llega a candidate."""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _marco import PASS, FAIL, BLOCKED, StoreDesechable, correr_solo

IDEA = 'idear'
HIPOTESIS = 'Un diagrama roto no llega a candidate.'

def correr():
    from nightshift import config, dream, redact
    bueno = ("flowchart LR\n"
             "  A[clave cruda] -->|se normaliza| B[clave limada]\n"
             "  B --> C[(indice)]\n"
             "  A -->|consulta sin limar| C")
    malos = {
        "sin cabecera": "A --> B\n  B --> C",
        "corchete abierto": "flowchart LR\n  A[clave --> B[otra]",
        "backtick": "flowchart LR\n  A[`x`] --> B",
        "vacio": "",
        "un plano": "\n".join(["flowchart LR"] + ["  N%d --> N%d" % (i, i + 1)
                                                  for i in range(20)]),
    }
    if dream.validate_diagram(bueno):
        return FAIL, "rechaza un diagrama bien formado: %s" % dream.validate_diagram(bueno)
    sin_detectar = [n for n, d in malos.items() if not dream.validate_diagram(d)]
    if sin_detectar:
        return FAIL, "pasaron diagramas rotos: %s" % sin_detectar
    red = redact.Redactor(identifiers=[], deny_paths=config.DEFAULT_DENY_PATHS, home_dir=None)
    _, _, _, problemas = dream.validate(
        {"pattern": "Una etapa valida la forma y nunca el contenido.",
         "diagram": malos["corchete abierto"]}, redactor=red, home_dir=None)
    if not [p for p in problemas if p.startswith("diagram:")]:
        return FAIL, "un diagrama roto no voltea la consolidacion"
    return PASS, ("1 bueno pasa, %d rotos se rechazan, y el rechazo voltea la\n"
                  "consolidacion (entra al mismo bucle de reintentos que una fuga).\n"
                  "OJO: esto valida SINTAXIS, nunca verdad. El diagrama de la candidata\n"
                  "falsa del 2026-08-28 es Mermaid perfectamente valido." % len(malos))

if __name__ == "__main__":
    sys.exit(correr_solo(sys.modules[__name__]))
