"""H20 — Un oráculo externo se enchufa como comando, no como servicio."""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _marco import PASS, FAIL, BLOCKED, StoreDesechable, correr_solo

IDEA = 'oraculos'
HIPOTESIS = 'Un oráculo externo se enchufa como comando, no como servicio.'

def correr():
    from nightshift import config
    if "oracle_command" in config.DEFAULTS:
        return PASS, "existe `oracle_command`"
    return FAIL, ("no existe. Hoy el unico oraculo es una persona tecleando\n"
                  "`nightshift resolve`.\n"
                  "El diseno propuesto respeta ADR-003 sin negociarlo: el oraculo es un\n"
                  "COMANDO, no un servicio — lee una pregunta por stdin y escribe un\n"
                  "veredicto por stdout, igual que `model_command`. Asi sirve un humano,\n"
                  "un script, otro modelo o una API que envuelva el usuario, con su\n"
                  "credencial y su riesgo, sin que nightshift hable con la red nunca.\n"
                  "Es O3 del plan §7, y va con ADR-006.")

if __name__ == "__main__":
    sys.exit(correr_solo(sys.modules[__name__]))
