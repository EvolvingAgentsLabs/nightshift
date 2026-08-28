"""H12 — Una refutada deja de enganchar; una confirmada no asciende de peso."""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _marco import PASS, FAIL, BLOCKED, StoreDesechable, correr_solo

IDEA = 'adelante'
HIPOTESIS = 'Una refutada deja de enganchar; una confirmada no asciende de peso.'

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
    def rank(estado):
        with StoreDesechable() as d:
            tid = _candidata(d, proyectadas=['los totales de un reporte no cierran porque un registro aparece duplicado'])
            if estado:
                d.store.resolve_projection(d.conn, d.store.projections_of(d.conn, tid)[0]["id"],
                                           status=estado, evidence="motivo suficiente",
                                           resolved_by="alguien")
            s = retrieve.candidates(d.conn, task_type="debug_test_failure",
                                    repo_fingerprint="f" * 64, cfg=config.load(),
                                    prompt='los totales del reporte no cierran y un cliente aparece duplicado')
            return (s[0][0], s[0][1]) if s else (0.0, "")
    abierta, m_abierta = rank(None)
    refutada, m_refutada = rank("refuted")
    confirmada, m_confirmada = rank("confirmed")
    if "projected_match" not in m_abierta:
        return FAIL, "la abierta no engancha: el experimento no prueba nada"
    if "projected_match" in m_refutada:
        return FAIL, "una refutada sigue enganchando"
    if "projected_match" not in m_confirmada:
        return FAIL, "una confirmada dejo de enganchar: resolver castiga a quien resuelve"
    if abs(confirmada - abierta) > 0.01:
        return FAIL, "confirmarla le cambio el peso: %.3f -> %.3f" % (abierta, confirmada)
    return PASS, ("refutada %.2f < abierta %.2f, y confirmada = abierta.\n"
                  "Que el mecanismo haya acertado no vuelve a esta sesion la que lo\n"
                  "observo: si confirmarla la subiera, la frontera de ADR-004 dejaria de\n"
                  "existir despues de la primera resolucion." % (refutada, abierta))

if __name__ == "__main__":
    sys.exit(correr_solo(sys.modules[__name__]))
