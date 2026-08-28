"""H20 — Un oráculo externo se enchufa como comando, no como servicio."""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _marco import PASS, FAIL, BLOCKED, StoreDesechable, correr_solo

IDEA = "oraculos"
HIPOTESIS = "Un oraculo externo se enchufa como comando, no como servicio."

FALSO = """#!/usr/bin/env python3
import json, sys
pregunta = json.load(sys.stdin)
print(json.dumps({"status": "confirmed",
                  "evidence": "la vi en produccion: " + pregunta["projection"][:30]}))
"""
ROTO = """#!/usr/bin/env python3
print("esto no es json")
"""
SIN_MOTIVO = """#!/usr/bin/env python3
import json, sys
sys.stdin.read()
print(json.dumps({"status": "refuted", "evidence": ""}))
"""


def correr():
    import stat, tempfile
    from nightshift import config, oracle
    if "oracle_command" not in config.DEFAULTS:
        return FAIL, "no hay `oracle_command` en la config"
    with tempfile.TemporaryDirectory(prefix="nightshift-orac-") as d:
        rutas = {}
        for nombre, cuerpo in (("bueno", FALSO), ("roto", ROTO), ("sin_motivo", SIN_MOTIVO)):
            ruta = os.path.join(d, nombre + ".py")
            open(ruta, "w").write(cuerpo)
            os.chmod(ruta, os.stat(ruta).st_mode | stat.S_IEXEC)
            rutas[nombre] = [sys.executable, ruta]

        respuesta = oracle.ask(rutas["bueno"], projection="los totales no cierran",
                               pattern="un indice se arma normalizando la clave")
        if respuesta["status"] != "confirmed" or "produccion" not in respuesta["evidence"]:
            return FAIL, "el oraculo bueno no contesto bien: %r" % respuesta
        for nombre in ("roto", "sin_motivo"):
            try:
                oracle.ask(rutas[nombre], projection="x")
            except oracle.OracleError:
                continue
            return FAIL, "el oraculo `%s` no fue rechazado" % nombre

    # Y la parte que ADR-006 defiende: nightshift no habla con la red, ni acá ni en
    # ningún lado. El módulo del oráculo no puede importar red.
    import inspect
    fuente = inspect.getsource(oracle)
    for prohibido in ("import socket", "import urllib", "import http", "requests"):
        if prohibido in fuente:
            return FAIL, "el modulo del oraculo importa red: %s" % prohibido
    return PASS, ("un ejecutable cualquiera contesta por stdin/stdout; uno que devuelve\n"
                  "basura y uno que resuelve sin motivo se rechazan (un oraculo roto NO es\n"
                  "un `open`: eso confundiria una falla de plomeria con un dato).\n"
                  "Y el modulo no importa red: el oraculo es un COMANDO del usuario, con\n"
                  "su credencial y su riesgo, sin que nightshift hable con nadie (ADR-006).")


if __name__ == "__main__":
    sys.exit(correr_solo(sys.modules[__name__]))
