"""H01 — lo capturado tiene contenido, no sólo estructura."""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _marco import PASS, FAIL, StoreDesechable, correr_solo

IDEA = "CTE"
HIPOTESIS = "La captura guarda el contenido de cada paso, no sólo su forma."


def correr():
    with StoreDesechable() as d:
        tid = d.store.open_trajectory(d.conn, session_id="s", repo_fingerprint="f" * 64,
                                      task_type="debug_test_failure", base_commit="abc1234",
                                      redaction={"redactor_version": "0.1.0"})
        d.store.append_step(d.conn, tid, kind="tool_failure", tool="run_shell",
                            args={"command": "make check"},
                            error_message="Exit code 1: el decodificador explota")
        pasos = d.store.steps_of(d.conn, tid)
        con_texto = [p for p in pasos if (p["error_message"] or p["result_summary"])]
    if len(con_texto) != len(pasos):
        return FAIL, "%d de %d pasos llegaron vacíos" % (len(pasos) - len(con_texto), len(pasos))
    return PASS, "%d/%d pasos con contenido. El modo de falla histórico de este repo es\n" \
                 "el silencio: estructura llena y campos vacíos (spec §5.9)." % (
                     len(con_texto), len(pasos))


if __name__ == "__main__":
    sys.exit(correr_solo(sys.modules[__name__]))
