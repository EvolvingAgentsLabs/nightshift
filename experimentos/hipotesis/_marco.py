"""El marco mínimo de un experimento por hipótesis.

Cada archivo `H<nn>-*.py` de esta carpeta valida **una** hipótesis del proyecto y nada
más. La regla que los hace útiles como cola de trabajo:

- **`PASS` significa que se comprobó, no que se cree.** Un experimento que no ejercita
  código no es un experimento: es una opinión con nombre de archivo.
- **`FAIL` es un resultado, no un error.** Es la lista de lo que falta, y es el punto.
- **`BLOCKED` es distinto de `FAIL`**: la hipótesis no se puede comprobar todavía porque
  depende de una decisión humana o de material que no existe. Confundirlos convierte una
  espera en un fracaso, y este repo ya pagó esa confusión.

Cada uno corre solo (`python3 experimentos/hipotesis/H03-*.py`) y todos juntos con
`nightshift experiments`.
"""

import os
import sys
import tempfile
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent.parent
if str(RAIZ) not in sys.path:
    sys.path.insert(0, str(RAIZ))

PASS, FAIL, BLOCKED = "PASS", "FAIL", "BLOCKED"


class StoreDesechable:
    """Un store nuevo en un HOME temporal. Nunca toca el store real.

    Un experimento que escribe en `~/.nightshift` deja de ser reproducible en la segunda
    corrida, y peor: ensucia la evidencia que el proyecto usa para decidir.
    """

    def __enter__(self):
        self._home = os.environ.get("HOME")
        self._dir = tempfile.TemporaryDirectory(prefix="nightshift-hip-")
        os.environ["HOME"] = self._dir.name
        for modulo in ("nightshift.config", "nightshift.store"):
            sys.modules.pop(modulo, None)
        from nightshift import config, store
        config.write_default(config.config_path()) if hasattr(config, "write_default") else None
        self.store = store
        self.conn = store.connect()
        return self

    def __exit__(self, *exc):
        try:
            self.conn.close()
        finally:
            if self._home is not None:
                os.environ["HOME"] = self._home
            self._dir.cleanup()
        return False


def correr_solo(modulo):
    """Para que cada archivo se pueda ejecutar directamente y decir algo legible."""
    estado, detalle = modulo.correr()
    print("%s  %s" % (estado, modulo.HIPOTESIS))
    for linea in str(detalle).splitlines():
        print("      %s" % linea)
    return 0 if estado == PASS else 1
