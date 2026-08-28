"""H07 — Dream proyecta síntomas que nadie observó, y no los mezcla con los observados."""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _marco import PASS, FAIL, BLOCKED, StoreDesechable, correr_solo

IDEA = 'adelante'
HIPOTESIS = 'Dream proyecta síntomas que nadie observó, y no los mezcla con los observados.'

def correr():
    from nightshift import config, dream, redact
    red = redact.Redactor(identifiers=[], deny_paths=config.DEFAULT_DENY_PATHS, home_dir=None)
    abstraction, _, _, problemas = dream.validate({
        "pattern": "Una etapa valida la forma del registro y nunca su contenido.",
        "signals": ["el test falla al comparar dos claves"],
        "projected_signals": ["un reporte suma dos veces el mismo registro",
                              "el test falla al comparar dos claves"]},
        redactor=red, home_dir=None)
    if problemas:
        return FAIL, "la validacion rechazo: %s" % problemas
    if abstraction.get("signals") != ["el test falla al comparar dos claves"]:
        return FAIL, "una proyeccion se colo entre las senales observadas"
    proyectadas = abstraction.get("_projected_signals") or []
    if proyectadas != ["un reporte suma dos veces el mismo registro"]:
        return FAIL, "proyecciones inesperadas: %r" % proyectadas
    return PASS, ("lo proyectado viaja aparte, y repetir una observada no proyecta nada:\n"
                  "duplicarla la haria sumar dos veces en el ranking siendo la misma frase.")

if __name__ == "__main__":
    sys.exit(correr_solo(sys.modules[__name__]))
