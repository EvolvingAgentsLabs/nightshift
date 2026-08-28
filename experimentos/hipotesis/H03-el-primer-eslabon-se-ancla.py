"""H03 — la hipótesis se ancla a una observación, o no existe."""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _marco import PASS, FAIL, StoreDesechable, correr_solo

IDEA = "CTE"
HIPOTESIS = "El primer eslabón de la cadena cita un paso que observa, o queda en null."


def correr():
    from nightshift import config, dream, redact
    red = redact.Redactor(identifiers=[], deny_paths=config.DEFAULT_DENY_PATHS, home_dir=None)
    base = {"pattern": "Una etapa valida la forma del registro y nunca su contenido."}
    casos = {
        "sin ancla": (dict(base, hypothesis="se creyó que era el parser"), None),
        "ancla inexistente": (dict(base, hypothesis="idem", hypothesis_step=99), None),
        "ancla a lectura": (dict(base, hypothesis="idem", hypothesis_step=7), None),
        "ancla válida": (dict(base, hypothesis="se creyó que era el parser",
                              hypothesis_step=3), "se creyó que era el parser"),
    }
    fallos = []
    for nombre, (datos, esperado) in casos.items():
        _, _, hipo, _ = dream.validate(datos, redactor=red, home_dir=None,
                                       observation_indices={3})
        if hipo != esperado:
            fallos.append("%s: %r (esperado %r)" % (nombre, hipo, esperado))
    if fallos:
        return FAIL, "\n".join(fallos)
    return PASS, "4 casos. El de 'ancla a lectura' es el que reproduce la candidata falsa\n" \
                 "del 2026-08-28: anclar por índice no alcanzaba, hay que anclar a un paso\n" \
                 "que observe."


if __name__ == "__main__":
    sys.exit(correr_solo(sys.modules[__name__]))
