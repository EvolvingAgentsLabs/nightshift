"""H02 — un `grep` es el repo hablando de sí mismo, no una observación."""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _marco import PASS, FAIL, StoreDesechable, correr_solo

IDEA = "CTE"
HIPOTESIS = "Una lectura del repositorio no cuenta como evidencia de esta sesión."


def correr():
    from nightshift import dream
    with StoreDesechable() as d:
        tid = d.store.open_trajectory(d.conn, session_id="s", repo_fingerprint="f" * 64,
                                      task_type="debug_test_failure", base_commit="abc1234",
                                      redaction={"redactor_version": "0.1.0"})
        casos = [("grep -n bandera hook.py", True), ("cat doc/00-spec.md", True),
                 ("git log --oneline -5", True), ("make check", False),
                 ("python3 -m unittest -q", False)]
        for comando, _ in casos:
            d.store.append_step(d.conn, tid, kind="tool_use", tool="run_shell",
                                args={"command": comando}, result_summary="salida")
        d.store.append_step(d.conn, tid, kind="tool_failure", tool="run_shell",
                            args={"command": "grep -n algo x.py"}, error_message="Exit code 2")
        pasos = d.store.steps_of(d.conn, tid)
        obtenido = [dream.es_lectura(p) for p in pasos]
    esperado = [e for _, e in casos] + [False]   # un fallo nunca es lectura
    if obtenido != esperado:
        return FAIL, "clasificación %s, esperada %s" % (obtenido, esperado)
    return PASS, "5 comandos + 1 fallo clasificados bien. Un fallo con `grep` sigue siendo\n" \
                 "observación: salir distinto de cero es evidencia de esta sesión."


if __name__ == "__main__":
    sys.exit(correr_solo(sys.modules[__name__]))
