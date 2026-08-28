"""H11 — Una conjetura se puede resolver, y no sin evidencia ni sin autor."""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _marco import PASS, FAIL, BLOCKED, StoreDesechable, correr_solo

IDEA = 'adelante'
HIPOTESIS = 'Una conjetura se puede resolver, y no sin evidencia ni sin autor.'

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
        tid = _candidata(d, proyectadas=['los totales de un reporte no cierran porque un registro aparece duplicado'])
        filas = d.store.projections_of(d.conn, tid)
        if not filas:
            return FAIL, "promover no dejo la conjetura con estado"
        pid = filas[0]["id"]
        for evidencia, autor in (("", "alguien"), ("   ", "alguien"), ("motivo", "")):
            try:
                d.store.resolve_projection(d.conn, pid, status="refuted",
                                           evidence=evidencia, resolved_by=autor)
            except ValueError:
                continue
            return FAIL, "resolvio con evidencia=%r autor=%r" % (evidencia, autor)
        d.store.resolve_projection(d.conn, pid, status="confirmed",
                                   evidence="la vi pasar el martes", resolved_by="alguien")
        fila = d.store.projections_of(d.conn, tid)[0]
        stats = d.store.projection_stats(d.conn)
    if fila["status"] != "confirmed" or not fila["evidence"] or not fila["resolved_by"]:
        return FAIL, "la resolucion quedo incompleta: %s" % dict(fila)
    return PASS, ("resuelta con evidencia y autor; sin cualquiera de los dos se rechaza.\n"
                  "Refutar sin motivo es olvidar con otro nombre, y confirmar sin motivo es\n"
                  "una explicacion plausible anotada como hallazgo.\n"
                  "acierto: %s de %d resueltas" % (stats["confirmed"], stats["resolved"]))

if __name__ == "__main__":
    sys.exit(correr_solo(sys.modules[__name__]))
