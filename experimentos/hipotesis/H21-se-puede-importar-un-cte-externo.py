"""H21 — Se puede importar una cadena de ejecución generada afuera."""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _marco import PASS, FAIL, BLOCKED, StoreDesechable, correr_solo

IDEA = "oraculos"
HIPOTESIS = "Se puede importar una cadena de ejecucion generada afuera, sin mezclarla con lo propio."


def correr():
    from nightshift import config, redact, retrieve
    with StoreDesechable() as d:
        propia = d.store.open_trajectory(d.conn, session_id="s", repo_fingerprint="f" * 64,
                                         task_type="debug_test_failure",
                                         base_commit="abc1234",
                                         redaction={"redactor_version": "0.1.0"})
        d.store.append_step(d.conn, propia, kind="tool_failure", tool="run_shell",
                            error_message="el decodificador explota", decisive=True)
        d.store.close_trajectory(d.conn, propia, result="tests_passed")
        doc = d.store.export_trajectory(d.conn, propia)
        doc["steps"][0]["error_message"] = "el decodificador explota en /home/otro/.ssh/id_rsa"
        red = redact.Redactor(identifiers=[], deny_paths=config.DEFAULT_DENY_PATHS,
                              home_dir=None)
        externa = d.store.import_trajectory(d.conn, doc, redactor=red)
        fila = d.store.get_trajectory(d.conn, externa)
        pasos = d.store.steps_of(d.conn, externa)
        scored = retrieve.candidates(d.conn, task_type="debug_test_failure",
                                     repo_fingerprint="f" * 64, cfg=config.load())
        texto, _ = retrieve.render(d.conn, scored, max_injected=5, native_memory=False,
                                   task_type="debug_test_failure",
                                   repo_fingerprint="f" * 64)
        pesos = {r["id"]: r["injection_weight"] for _, _, r in scored}

    if fila["origin"] != d.store.ORIGIN_EXTERNAL:
        return FAIL, "lo importado no quedo marcado como externo"
    if fila["injection_weight"] >= 0.3:
        return FAIL, "lo externo pesa %s: no puede llegar al peso de una cruda local" % fila["injection_weight"]
    if pesos.get(externa, 1) >= pesos.get(propia, 0):
        return FAIL, "lo importado no pesa menos que lo propio"
    if "id_rsa" in (pasos[0]["error_message"] or ""):
        return FAIL, "no se volvio a redactar de este lado: entro una ruta que el redactor tapa"
    if "IMPORTADA" not in texto:
        return FAIL, "la inyeccion no dice que la fila no se observo en esta maquina"
    return PASS, ("importada con origin=external y peso %.1f, por debajo de una cruda local\n"
                  "(0.3) y de una candidate (0.6). Se volvio a redactar de este lado: que\n"
                  "el que exporto diga que redacto no es comprobable desde aca.\n"
                  "Y la inyeccion lo anuncia en el encabezado, no en una nota al pie.\n"
                  "El numero exacto lo decide una persona; la desigualdad no se negocia."
                  % fila["injection_weight"])


if __name__ == "__main__":
    sys.exit(correr_solo(sys.modules[__name__]))
