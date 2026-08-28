"""H13 — El proyecto puede decir cuántas de sus conjeturas acertaron."""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _marco import PASS, FAIL, BLOCKED, StoreDesechable, correr_solo

IDEA = 'adelante'
HIPOTESIS = 'El proyecto puede decir cuántas de sus conjeturas acertaron.'

from nightshift import store

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
        vacio = d.store.projection_stats(d.conn)
        tid = _candidata(d, proyectadas=["una", "otra", "tercera"])
        sin_resolver = d.store.projection_stats(d.conn)
        filas = d.store.projections_of(d.conn, tid)
        d.store.resolve_projection(d.conn, filas[0]["id"], status="confirmed",
                                   evidence="la vi", resolved_by="a")
        d.store.resolve_projection(d.conn, filas[1]["id"], status="refuted",
                                   evidence="no puede", resolved_by="a")
        con = d.store.projection_stats(d.conn)
    if vacio["hit_rate"] is not None or sin_resolver["hit_rate"] is not None:
        return FAIL, "sin resolver ninguna el acierto tiene que ser None, no 0.0"
    if con["hit_rate"] != 0.5 or con["open"] != 1:
        return FAIL, "el marcador no cierra: %s" % con
    return PASS, ("3 proyectadas -> 1 confirmada, 1 refutada, 1 abierta, acierto 50%%.\n"
                  "Y con cero resueltas el acierto es None y NO 0.0: 'nadie miro' no es\n"
                  "'ninguna acerto', y confundirlos es el verde vacuo que ya costo un fix.")

if __name__ == "__main__":
    sys.exit(correr_solo(sys.modules[__name__]))
