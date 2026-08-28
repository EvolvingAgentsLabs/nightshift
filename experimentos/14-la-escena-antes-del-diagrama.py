"""Los dos medios de idear, sobre el mismo corpus: diagrama contra escena física (ADR-007).

**Qué mide esto y qué NO.**

Lo que mide: si el modelo **traduce de verdad**. El brazo `fisica` le pide algo que ningún
prompt de este repo le había pedido —salir del dominio del software y describir una
máquina— y hay un gate determinista que dice si lo hizo (`dream.validate_scene`). El número
es cuántos intentos necesitó cada campo para pasar, y es un número nuevo: hasta acá el
proyecto tenía medido el costo de idear (el triple de tokens de salida) y nada sobre si lo
pedido llega.

Lo que **no** mide, y es deliberado: si la escena transfiere mejor que el diagrama. Eso
necesita un conjunto retenido que ninguno de los dos brazos haya visto, y el único que
existe —los tres síntomas de `cbbd7ff0`— **está gastado**: se usó para diagnosticar (`09`),
para comparar brazos (`07`, H17) y para escribir dos reglas del prompt. El prompt del brazo
físico lo escribió alguien que había leído esos tres síntomas el mismo día. Medir contra
ellos daría un número, y sería entrenar contra el test.

Por eso este script imprime las dos salidas para **mirarlas**, no para puntuarlas, y el
veredicto vive en H23, que está `BLOCKED` hasta que haya material nuevo
(`experimentos/retenido/README.md`).

Cuesta dos llamadas al modelo: una por brazo.
"""

import argparse
import json
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ))

from nightshift import config, dream, redact, store          # noqa: E402


def _envolver(texto, ancho=76):
    import textwrap
    salida = []
    for parrafo in (texto or "").splitlines():
        salida += textwrap.wrap(parrafo, ancho) or [""]
    return salida


def correr_brazo(conn, modelo, grupo, modo, redactor):
    """Un brazo, con el bucle de reintentos de verdad: lo que se cuenta es cuántos
    intentos necesitó el modelo para que la respuesta pase los gates."""
    prompt = dream.build_prompt(conn, grupo, modo=modo)
    problemas, data = [], {}
    for intento in range(1 + dream.REINTENTOS):
        entrada = prompt if intento == 0 else prompt + dream.RETRY_SUFFIX % "\n".join(
            "- %s" % p for p in problemas)
        data = modelo.ask_json(entrada)
        abstraction, valid_when, hypothesis, problemas = dream.validate(
            data, redactor=redactor, home_dir=None, modo=modo)
        if not problemas:
            return {"modo": modo, "intentos": intento + 1, "ok": True,
                    "abstraction": abstraction, "ultimo_rechazo": [], "raw": data}
        rechazo = list(problemas)
    return {"modo": modo, "intentos": 1 + dream.REINTENTOS, "ok": False,
            "abstraction": None, "ultimo_rechazo": rechazo, "raw": data}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--trajectory", default=None,
                    help="qué trayectoria consolidar (por defecto, el grupo más grande)")
    ap.add_argument("--model", default=None)
    args = ap.parse_args()

    conn = store.connect()
    if args.trajectory:
        fila = conn.execute("SELECT * FROM trajectories WHERE id LIKE ?",
                            (args.trajectory + "%",)).fetchone()
        if fila is None:
            raise SystemExit("no encuentro una trayectoria que empiece con %s"
                             % args.trajectory)
        grupo = [fila]
    else:
        grupos = dream.groups(conn, lookback_days=3650)
        if not grupos:
            raise SystemExit("no hay trayectorias cerradas que consolidar")
        grupo = max(grupos, key=len)

    cfg = config.load()
    if args.model:
        cfg["model_command"] = args.model.split()
    comando = dream.detect_command(cfg)
    if not comando:
        raise SystemExit("no hay modelo disponible: este experimento necesita uno")
    modelo = dream.LocalModel(comando, timeout=cfg.get("dream_timeout_seconds", 180))
    redactor = redact.Redactor(identifiers=dream.redactor_identifiers(str(RAIZ)),
                               deny_paths=cfg["deny_paths"], home_dir=str(Path.home()))

    print("corpus: %d trayectoria(s) (%s)" % (len(grupo), grupo[0]["task_type"]))
    print("dos llamadas al modelo, una por brazo. El store real NO se toca: esto valida,")
    print("no promueve.")
    print()

    salidas = {}
    for modo in dream.MODOS_DE_IDEACION:
        print("▸ brazo %s" % modo.upper())
        salidas[modo] = correr_brazo(conn, modelo, grupo, modo, redactor)
        r = salidas[modo]
        print("  intentos hasta pasar los gates: %d%s"
              % (r["intentos"], "" if r["ok"] else "  ← NUNCA pasó"))
        if not r["ok"]:
            for p in r["ultimo_rechazo"]:
                print("    rechazo: %s" % p)
        abst = r["abstraction"] or {}
        if abst.get("_diagram"):
            print("  dibujo:")
            for linea in abst["_diagram"].splitlines():
                print("    %s" % linea)
        if abst.get("_logogram"):
            print("  logograma: %s" % abst["_logogram"])
        if abst.get("_physical_scene"):
            print("  escena:")
            for linea in _envolver(abst["_physical_scene"]):
                print("    %s" % linea)
        if abst.get("pattern"):
            print("  patrón:")
            for linea in _envolver(abst["pattern"]):
                print("    %s" % linea)
        for señal in (abst.get("_projected_signals") or [])[:3]:
            print("  proyectado: %s" % señal)
        print()

        # Sólo se guarda lo que pasó los gates. Una respuesta rechazada es texto de
        # modelo que nadie revisó por fugas —el rechazo pudo ser justamente por eso— y
        # este archivo se commitea al repo.
        if r["ok"]:
            destino = RAIZ / "experimentos" / "salidas" / ("14-%s.json" % modo)
            destino.parent.mkdir(exist_ok=True)
            destino.write_text(json.dumps(r["raw"], indent=2, ensure_ascii=False)
                               + "\n", encoding="utf-8")
        else:
            print("  (no se guarda la salida: no pasó los gates y nadie la revisó)")
    conn.close()

    print("-" * 72)
    print("LO QUE ESTO DICE: si el modelo hace lo que se le pide. El brazo fisica pasó")
    print("sus gates en %d intento(s); el brazo mermaid, en %d."
          % (salidas["fisica"]["intentos"], salidas["mermaid"]["intentos"]))
    print()
    print("LO QUE NO DICE, y conviene decirlo antes de que alguien lo cite mal: cuál de")
    print("los dos transfiere. El único conjunto retenido que existe está gastado, y el")
    print("prompt del brazo físico se escribió con esos síntomas a la vista. Medir contra")
    print("ellos sería entrenar contra el test. El veredicto es H23, y está BLOCKED.")
    print()
    print("n = 1 corpus, 1 corrida por brazo. Esto no sostiene ADR-007 ni tumba ADR-004.")


if __name__ == "__main__":
    main()
