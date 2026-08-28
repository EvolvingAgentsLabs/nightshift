"""H06 — nightshift detecta dónde termina un capítulo."""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _marco import PASS, FAIL, BLOCKED, StoreDesechable, correr_solo

IDEA = "CTE"
HIPOTESIS = "nightshift detecta donde termina un capitulo."


def correr():
    from nightshift import dream
    with StoreDesechable() as d:
        tid = d.store.open_trajectory(d.conn, session_id="s", repo_fingerprint="f" * 64,
                                      task_type="implement_feature", base_commit="abc1234",
                                      redaction={"redactor_version": "0.1.0"})
        def paso(comando, kind="tool_use", **kw):
            d.store.append_step(d.conn, tid, kind=kind, tool="run_shell",
                                args={"command": comando}, result_summary="salida", **kw)
        for _ in range(6):
            paso("grep -n algo archivo.py")
        paso("make check")                      # borde 1
        for _ in range(6):
            paso("sed -n '1,20p' archivo.py")
        paso("git commit -m 'x'")               # borde 2
        for _ in range(6):
            paso("cat otro.py")
        paso("make check", kind="tool_failure") # un gate en ROJO no cierra nada
        bordes = dream.suggest_chapters(d.conn, tid)

    motivos = [b["motivo"] for b in bordes]
    if len(bordes) != 2:
        return FAIL, "se esperaban 2 bordes y salieron %d: %s" % (len(bordes), bordes)
    if "test" not in motivos[0] or "commit" not in motivos[1]:
        return FAIL, "los motivos no son los esperados: %s" % motivos
    return PASS, ("2 bordes en [%d] y [%d], y el gate en ROJO del final no corta nada:\n"
                  "un capitulo termina cuando el trabajo CERRO algo.\n"
                  "SUGIERE, NO CORTA, y la diferencia no es timidez: nadie midio todavia\n"
                  "si estos bordes producen candidatas mejores que un dia entero. Con\n"
                  "`sleep` andando ese numero se puede medir, y medirlo es lo que habilita\n"
                  "sellar solo. Automatizar antes seria estimar en vez de medir."
                  % (bordes[0]["idx"], bordes[1]["idx"]))


if __name__ == "__main__":
    sys.exit(correr_solo(sys.modules[__name__]))
