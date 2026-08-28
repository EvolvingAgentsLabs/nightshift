"""H19 — Git puede decir si el fix de una trayectoria sobrevivió."""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _marco import PASS, FAIL, BLOCKED, StoreDesechable, correr_solo

IDEA = 'oraculos'
HIPOTESIS = 'Git puede decir si el fix de una trayectoria sobrevivió.'

def correr():
    from nightshift import dream
    if any(hasattr(dream, n) for n in ("survived", "git_oracle", "corroborate")):
        return PASS, "existe el oraculo de git"
    return FAIL, ("no existe. La trayectoria guarda `base_commit` y nadie lo usa para\n"
                  "preguntar si el commit se revirtio, si los archivos se volvieron a\n"
                  "tocar poco despues, o si el test que se agrego sigue existiendo.\n"
                  "Es lo mas parecido a verificacion que se puede tener sin M5, sin\n"
                  "modelo, sin red y sin credencial. Y NO es verify: corrobora, que es una\n"
                  "tercera categoria y no un ascenso.\n"
                  "Es O2 del plan §7.")

if __name__ == "__main__":
    sys.exit(correr_solo(sys.modules[__name__]))
