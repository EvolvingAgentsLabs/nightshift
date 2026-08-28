"""H04 — La cadena tiene eslabones explícitos: qué corrección arregló qué error."""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _marco import PASS, FAIL, BLOCKED, StoreDesechable, correr_solo

IDEA = "CTE"
HIPOTESIS = "La cadena tiene eslabones explicitos: que correccion arreglo que error."


def correr():
    from nightshift import dream
    with StoreDesechable() as d:
        tid = d.store.open_trajectory(d.conn, session_id="s", repo_fingerprint="f" * 64,
                                      task_type="debug_test_failure", base_commit="abc1234",
                                      redaction={"redactor_version": "0.1.0"})
        d.store.append_step(d.conn, tid, kind="tool_failure", tool="run_shell",
                            error_message="el decodificador explota", decisive=True)
        d.store.append_step(d.conn, tid, kind="tool_use", tool="edit_file",
                            result_summary="se subio el timeout")
        d.store.mark_last_contradicted(d.conn, tid)      # el usuario dijo que estaba mal
        d.store.append_step(d.conn, tid, kind="tool_use", tool="edit_file",
                            result_summary="se fijo la codificacion")
        d.store.append_step(d.conn, tid, kind="observation",
                            result_summary="fin de turno")
        d.store.close_trajectory(d.conn, tid, result="tests_passed")
        eslabones = dream.cadena(d.store.steps_of(d.conn, tid))

    por_tipo = {e["eslabon"]: e for e in eslabones}
    if "fallo" not in por_tipo:
        return FAIL, "no se reconocio el fallo"
    correccion = por_tipo.get("correccion")
    if not correccion:
        return FAIL, "no se reconocio la correccion: %s" % [e["eslabon"] for e in eslabones]
    if correccion["corrects"] != 1:
        return FAIL, "la correccion apunta a %r y no al paso contradicho (1)" % correccion["corrects"]
    if "fix" not in por_tipo or por_tipo["fix"]["idx"] != 2:
        return FAIL, "el fix no es el ultimo paso que hizo algo: %r" % por_tipo.get("fix")
    return PASS, ("la correccion en [%d] apunta al paso [%d] que el usuario contradijo, y\n"
                  "el fix es el ultimo paso que HIZO algo (el sello del turno no arregla\n"
                  "nada).\n"
                  "Se DERIVA de lo persistido y no de banderas nuevas: `contradicted`,\n"
                  "`decisive`, el orden y el comando ya estaban todos guardados, asi que\n"
                  "se puede recalcular hacia atras sobre trayectorias viejas."
                  % (correccion["idx"], correccion["corrects"]))


if __name__ == "__main__":
    sys.exit(correr_solo(sys.modules[__name__]))
