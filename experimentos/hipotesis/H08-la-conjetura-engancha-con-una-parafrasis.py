"""H08 — Una conjetura engancha cuando el usuario describe el síntoma con sus palabras."""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _marco import PASS, FAIL, BLOCKED, StoreDesechable, correr_solo

IDEA = 'adelante'
HIPOTESIS = 'Una conjetura engancha cuando el usuario describe el síntoma con sus palabras.'

from nightshift import config, retrieve

def _candidata(d, proyectadas=None, diagrama=None):
    tid = d.store.open_trajectory(d.conn, session_id="s", repo_fingerprint="f" * 64,
                                  task_type="debug_test_failure", base_commit="abc1234",
                                  redaction={"redactor_version": "0.1.0"})
    d.store.append_step(d.conn, tid, kind="tool_failure", tool="run_shell",
                        error_message="KeyError en el borde", decisive=True)
    d.store.close_trajectory(d.conn, tid, result="tests_passed")
    d.store.promote_to_candidate(
        d.conn, tid,
        abstraction={"pattern": "El indice se arma normalizando la clave pero la consulta "
                                "busca con la clave cruda.",
                     "signals": ["una clave que esta en el indice levanta KeyError"]},
        valid_when=[], hypothesis=None, weight=0.6,
        projected_signals=proyectadas, diagram=diagrama)
    return tid


def correr():
    PROY = "los totales de un reporte no cierran porque un registro aparece duplicado"
    PARAFRASIS = "los totales del reporte no cierran y un cliente aparece duplicado"
    AJENO = "el certificado ssl del dominio vencio y el deploy no arranca"
    with StoreDesechable() as d:
        _candidata(d, proyectadas=[PROY])
        cfg = config.load()

        def motivos(prompt):
            s = retrieve.candidates(d.conn, task_type="debug_test_failure",
                                    repo_fingerprint="f" * 64, cfg=cfg, prompt=prompt)
            return s[0][1] if s else ""
        con, control = motivos(PARAFRASIS), motivos(AJENO)
    if "projected_match" not in con:
        return FAIL, "la parafrasis no engancho: %s" % con
    if "projected_match" in control:
        return FAIL, "FALSO POSITIVO: un prompt ajeno engancho (%s)" % control
    return PASS, ("parafrasis engancha, control negativo no.\n"
                  "Es lo que arreglo la enmienda 0.3.6: con un piso unico el enganche se\n"
                  "caia a cero en cuanto el usuario lo decia con sus palabras, que es la\n"
                  "unica forma en que alguien lo dice.")

if __name__ == "__main__":
    sys.exit(correr_solo(sys.modules[__name__]))
