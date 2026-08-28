"""H05 — Se puede sellar el capítulo en curso sin que la sesión deje de capturar."""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _marco import PASS, FAIL, BLOCKED, StoreDesechable, correr_solo

IDEA = 'CTE'
HIPOTESIS = 'Se puede sellar el capítulo en curso sin que la sesión deje de capturar.'

def correr():
    from nightshift import dream, hook
    with StoreDesechable() as d:
        tid = d.store.open_trajectory(d.conn, session_id="viva", repo_fingerprint="f" * 64,
                                      task_type="debug_test_failure", base_commit="abc1234",
                                      redaction={"redactor_version": "0.1.0"})
        d.store.append_step(d.conn, tid, kind="tool_use", tool="run_shell",
                            result_summary="trabajo del capitulo")
        estado, _ = dream.seal_chapter(d.conn, d.store.get_trajectory(d.conn, tid))
        abierta = d.store.active_trajectory(d.conn, "viva")
        nuevo = hook._ensure_trajectory(d.conn, {"session_id": "viva", "cwd": "."}, {})
        pasos = len(d.store.steps_of(d.conn, tid))
    if estado != "closed":
        return FAIL, "el capitulo quedo en %r" % estado
    if abierta is not None:
        return FAIL, "quedo una trayectoria abierta despues de sellar"
    if not nuevo or nuevo == tid:
        return FAIL, "la sesion no abrio una trayectoria nueva: la captura se apago"
    return PASS, ("sellado, y el proximo evento de hook abrio otra. %d paso(s) quedaron en\n"
                  "el capitulo y ninguno se movio.\n"
                  "Es el invariante que puede apagar la captura EN SILENCIO: los hooks\n"
                  "salen 0 pase lo que pase." % pasos)

if __name__ == "__main__":
    sys.exit(correr_solo(sys.modules[__name__]))
