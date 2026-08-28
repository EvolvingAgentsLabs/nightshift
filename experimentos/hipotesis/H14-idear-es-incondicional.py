"""H14 — No hay ninguna configuración que apague la ideación."""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _marco import PASS, FAIL, BLOCKED, StoreDesechable, correr_solo

IDEA = 'idear'
HIPOTESIS = 'No hay ninguna configuración que apague la ideación.'

# La marca literal del bloque de ideación. Con acento: `"IDEÁ".upper()` sigue
# teniendo `Á`, así que comparar contra "IDEA" no matchea nunca — y el
# experimento daba FAIL sobre código que funciona.
MARCA = "IDE\u00c1"


def correr():
    from nightshift import config, dream
    if "consolidation_strategy" in config.DEFAULTS:
        return FAIL, "volvio la clave de config que podia apagar la ideacion"
    with StoreDesechable() as d:
        tid = d.store.open_trajectory(d.conn, session_id="s", repo_fingerprint="f" * 64,
                                      task_type="debug_test_failure", base_commit="abc1234",
                                      redaction={"redactor_version": "0.1.0"})
        d.store.append_step(d.conn, tid, kind="tool_failure", tool="run_shell",
                            error_message="KeyError", decisive=True)
        d.store.close_trajectory(d.conn, tid, result="tests_passed")
        grupo = [d.store.get_trajectory(d.conn, tid)]
        default = dream.build_prompt(d.conn, grupo)
        control = dream.build_prompt(d.conn, grupo, ideate=False)
        cfg = config.load()
        cfg["consolidation_strategy"] = "observed"
        vistos = []

        class Modelo:
            name = "fake"

            def ask_json(self, prompt):
                vistos.append(prompt)
                return {"pattern": "Una etapa valida la forma y nunca el contenido."}
        rep = dream.consolidate(d.conn, Modelo(), cfg=cfg, lookback_days=3650)
    if MARCA not in default:
        return FAIL, "el prompt por defecto no pide idear"
    if MARCA in control:
        return FAIL, "el brazo de control tambien idea: no hay control"
    if rep["strategy"] != "ideate" or MARCA not in vistos[0]:
        return FAIL, "una config vieja apago la ideacion"
    return PASS, ("idear es el default y una config con `observed` no lo apaga.\n"
                  "El brazo sin idear existe solo para experimentos/ideate.py: sin control\n"
                  "no se puede volver a medir la diferencia.")

if __name__ == "__main__":
    sys.exit(correr_solo(sys.modules[__name__]))
