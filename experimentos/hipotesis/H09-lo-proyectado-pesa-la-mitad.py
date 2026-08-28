"""H09 — Lo proyectado pesa la mitad de lo observado y se anuncia como conjetura."""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _marco import PASS, FAIL, BLOCKED, StoreDesechable, correr_solo

IDEA = 'adelante'
HIPOTESIS = 'Lo proyectado pesa la mitad de lo observado y se anuncia como conjetura.'

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
    with StoreDesechable() as d:
        _candidata(d, proyectadas=["los totales de un reporte no cierran"])
        scored = retrieve.candidates(d.conn, task_type="debug_test_failure",
                                     repo_fingerprint="f" * 64, cfg=config.load())
        texto, _ = retrieve.render(d.conn, scored, max_injected=3, native_memory=False,
                                   task_type="debug_test_failure", repo_fingerprint="f" * 64)
    if retrieve.W_PROJECTED_MATCH * 2 != retrieve.W_SIGNAL_MATCH:
        return FAIL, "el peso dejo de ser exactamente la mitad"
    if "NINGUNO fue observado" not in texto:
        return FAIL, "la inyeccion no dice que nadie lo observo"
    return PASS, ("W_PROJECTED_MATCH = W_SIGNAL_MATCH / 2, y la inyeccion lo anuncia.\n"
                  "No es calibracion: una la vio alguien y la otra la anticipo un modelo.")

if __name__ == "__main__":
    sys.exit(correr_solo(sys.modules[__name__]))
