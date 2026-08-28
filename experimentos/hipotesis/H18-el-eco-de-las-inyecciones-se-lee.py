"""H18 — Se puede saber en qué terminó la sesión que recibió cada memoria."""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _marco import PASS, FAIL, BLOCKED, StoreDesechable, correr_solo

IDEA = 'oraculos'
HIPOTESIS = 'Se puede saber en qué terminó la sesión que recibió cada memoria.'

def correr():
    with StoreDesechable() as d:
        fuente = d.store.open_trajectory(d.conn, session_id="vieja", repo_fingerprint="f" * 64,
                                         task_type="debug_test_failure", base_commit="abc1234",
                                         redaction={"redactor_version": "0.1.0"})
        d.store.close_trajectory(d.conn, fuente, result="tests_passed")
        receptora = d.store.open_trajectory(d.conn, session_id="nueva",
                                            repo_fingerprint="f" * 64,
                                            task_type="debug_test_failure",
                                            base_commit="abc1234",
                                            redaction={"redactor_version": "0.1.0"})
        d.store.record_injection(d.conn, session_id="nueva", source_trajectory=fuente,
                                 rank=1, score=1.0, reason="same_repo",
                                 into_trajectory=receptora)
        d.store.close_trajectory(d.conn, receptora, result="tests_passed")
        filas = d.conn.execute(
            "SELECT i.source_trajectory AS src, t.outcome_result AS fin"
            " FROM injections i LEFT JOIN trajectories t ON t.id = i.into_trajectory").fetchall()
    if not filas or filas[0]["fin"] != "tests_passed":
        return FAIL, "la arista inyeccion -> desenlace no se puede leer: %s" % [dict(f) for f in filas]
    return PASS, ("se lee: la memoria %s cayo en una sesion que termino en %s.\n"
                  "`into_trajectory` lo escribe el hook desde M2 y hasta el 2026-08-28\n"
                  "no lo leia NADIE (grep daba un solo uso, el INSERT).\n"
                  "Se reporta y no se rankea: es correlacion, el n es diminuto, y un\n"
                  "ranking que se alimenta de su propia salida deja de medir el repo."
                  % (filas[0]["src"][:8], filas[0]["fin"]))

if __name__ == "__main__":
    sys.exit(correr_solo(sys.modules[__name__]))
