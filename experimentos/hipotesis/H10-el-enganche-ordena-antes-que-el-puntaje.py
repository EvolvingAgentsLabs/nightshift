"""H10 — Una fila que engancha con el prompt llega antes que una con más puntaje que no engancha."""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _marco import PASS, FAIL, BLOCKED, StoreDesechable, correr_solo

IDEA = 'adelante'
HIPOTESIS = 'Una fila que engancha con el prompt llega antes que una con más puntaje que no engancha.'

def correr():
    from nightshift import config, context, retrieve
    PROY = "los totales de un reporte no cierran porque un registro aparece duplicado"
    PROMPT = "los totales del reporte no cierran y un cliente aparece duplicado"
    with StoreDesechable() as d:
        for i in range(3):
            t = d.store.open_trajectory(d.conn, session_id="ruido%d" % i,
                                        repo_fingerprint="f" * 64,
                                        task_type="debug_test_failure", base_commit="abc1234",
                                        redaction={"redactor_version": "0.1.0"})
            d.store.append_step(d.conn, t, kind="tool_failure", tool="run_shell",
                                error_message="el decodificador explota", decisive=True)
            d.store.close_trajectory(d.conn, t, result="tests_passed")
        tid = d.store.open_trajectory(d.conn, session_id="cand", repo_fingerprint="f" * 64,
                                      task_type=context.DEFAULT_TASK_TYPE,
                                      base_commit="abc1234",
                                      redaction={"redactor_version": "0.1.0"})
        d.store.append_step(d.conn, tid, kind="tool_use", tool="run_shell",
                            result_summary="se miro el indice")
        d.store.close_trajectory(d.conn, tid, result="unknown")
        d.store.promote_to_candidate(d.conn, tid,
                                     abstraction={"pattern": "El indice se arma normalizando."},
                                     valid_when=[], hypothesis=None, weight=0.6,
                                     projected_signals=[PROY])
        scored = retrieve.candidates(d.conn, task_type="debug_test_failure",
                                     repo_fingerprint="f" * 64, cfg=config.load(),
                                     prompt=PROMPT)
        primera = scored[0]
        resto = max(s for s, _, _ in scored[1:])
    if primera[2]["id"] != tid:
        return FAIL, "la unica fila que habla del problema no quedo primera"
    if primera[0] >= resto:
        return FAIL, "gano por puntaje: este experimento dejo de probar el orden"
    return PASS, ("primera con %.2f contra %.2f de la que le sigue: gana SIN ganar por\n"
                  "puntaje. Es una regla de orden, no un peso.\n"
                  "Sin esto, has_decisive_step + tests_passed son 2,5 puntos que no\n"
                  "dependen del prompt y tiran la conjetura fuera de la inyeccion."
                  % (primera[0], resto))

if __name__ == "__main__":
    sys.exit(correr_solo(sys.modules[__name__]))
