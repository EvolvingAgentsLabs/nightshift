"""H06 — nightshift detecta solo dónde termina un capítulo."""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _marco import PASS, FAIL, BLOCKED, StoreDesechable, correr_solo

IDEA = 'CTE'
HIPOTESIS = 'nightshift detecta solo dónde termina un capítulo.'

def correr():
    from nightshift import dream
    if any(hasattr(dream, n) for n in ("detect_chapters", "chapter_boundaries")):
        return PASS, "existe deteccion automatica de capitulos"
    return FAIL, ("el borde lo pone una persona con `nightshift sleep`. Detectarlo no\n"
                  "existe.\n"
                  "Y hay un motivo para no automatizarlo todavia: con `sleep` andando se\n"
                  "puede MEDIR si los bordes que elige una persona producen candidatas\n"
                  "mejores que un dia entero. Automatizar antes seria estimar en vez de\n"
                  "medir, que es el error que LATER.md documenta tres veces.")

if __name__ == "__main__":
    sys.exit(correr_solo(sys.modules[__name__]))
