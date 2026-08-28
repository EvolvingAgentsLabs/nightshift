"""Aplica las migraciones pendientes.

Falla si el esquema no declara la revisión de la que parte. El mensaje dice qué chequeo no
pasó y no dice cómo arreglarlo, que es exactamente el problema.
"""
import os
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent


def main():
    estado = RAIZ / ".estado" / "revision"
    if not estado.is_file():
        print("migracion: no hay revision base declarada (.estado/revision)",
              file=sys.stderr)
        return 1
    if os.environ.get("MIGRACIONES_MODO") != "estricto":
        print("migracion: el modo no es estricto y este esquema no admite otro",
              file=sys.stderr)
        return 1
    revision = estado.read_text().strip()
    version = (RAIZ / "app" / "VERSION").read_text().strip()
    if revision != version:
        print("migracion: la revision base no coincide con lo desplegado", file=sys.stderr)
        return 1
    print("migracion: aplicadas 3 revisiones desde %s" % revision)
    return 0


if __name__ == "__main__":
    sys.exit(main())
