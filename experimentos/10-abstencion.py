"""¿Dream se abstiene cuando no hay patrón, o siempre encuentra uno?

**Por qué esto es la pregunta más barata y más peligrosa del proyecto.** Los tres fixtures
del benchmark —familias A, C y D— fueron **diseñados con una causa compartida plantada a
mano**. Familia A tiene diez síntomas y un solo normalizador roto; familia C, el mismo
pipeline con la misma etapa que se traga la excepción en dos repos. Medir ahí si dream
encuentra el patrón es medir si encuentra algo que alguien puso para que encuentre.

Lo que nadie midió nunca es lo contrario: **si se abstiene cuando no hay nada.** El código
sabe recibir `{"pattern": null}` y los tests lo cubren con un modelo de mentira, o sea que
lo probado es la cañería, no la conducta. Un consolidador que siempre encuentra un patrón
es un generador de horóscopos con SQLite, y ninguna cantidad de resultados favorables lo
salva: si nunca dice que no, sus "sí" no informan.

**El montaje, y las dos mitades hacen falta.**

- **Grupo SIN patrón:** tres trayectorias que no comparten nada — un CSS que se corre, un
  timeout de base contra un índice que falta, y un JSON con una coma de más. Distinto
  dominio, distinto mecanismo, distinto desenlace. Lo correcto es `{"pattern": null}`.
- **Grupo CON patrón:** tres trayectorias que sí comparten mecanismo, escritas con
  síntomas distintos. Lo correcto es un patrón.

Sin la segunda mitad esto no mide nada: un modelo que contesta `null` siempre pasaría la
primera con nota perfecta.

**Qué NO decide.** No dice que la abstracción sea buena, ni que sirva. Dice si el sistema
es capaz de decir que no. Es un piso, no un techo.

Cuesta **dos llamadas al modelo** (una por grupo). Corre sobre un store desechable.

    make abstencion                                            # 4 grupos x 3 repeticiones
    python3 experimentos/10-abstencion.py --grupo sin-02,con-02

**Lo que dio, y por qué el corpus está en el fixture y no acá.** El 2026-08-28, con los
grupos `sin-01`/`con-01`: **0 de 3 abstenciones**. Se le agregó a `dream.PROMPT` una regla
dura —exigirse poder señalar el paso concreto de cada trayectoria donde el mismo mecanismo
actúa— y pasó a **3 de 3**, sin perder ninguna de las abstracciones correctas. Ese número
es una comprobación de que la palanca existe, **no** de que generalice: la regla se
escribió mirando ese corpus. Los grupos `sin-02` y `con-02` del fixture existen para eso —
`sin-02` es el caso difícil, trabajos que sólo comparten género.
"""

import argparse
import json
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ))
sys.path.insert(0, str(RAIZ / "experimentos"))

import camino_real                                                  # noqa: E402

# ------------------------------------------------------------------ el corpus

# El corpus vive en el fixture de la familia E, no acá: es el mismo material que va a usar
# el benchmark el día que `PREREG` se descongele, y dos copias de un corpus se separan.
FIXTURE = RAIZ / "bench" / "fixtures" / "familia-e" / "grupos.json"


def grupos(filtro=None):
    """Los grupos del fixture, con lo que se espera de cada uno."""
    datos = json.loads(FIXTURE.read_text(encoding="utf-8"))
    salida = []
    for g in datos["groups"]:
        if filtro and g["id"] not in filtro:
            continue
        salida.append(g)
    if not salida:
        raise SystemExit("ningún grupo con ese filtro en %s" % FIXTURE)
    return salida


def sembrar(d, trayectorias):
    """Deja los trabajos del grupo en el store desechable y devuelve las filas."""
    ids = []
    for i, caso in enumerate(trayectorias):
        tid = d.store.open_trajectory(d.conn, session_id="s%d" % i,
                                      repo_fingerprint=camino_real.REPO,
                                      task_type=caso["task_type"], base_commit="abc1234",
                                      redaction={"redactor_version": "0.1.0"})
        for j, paso in enumerate(caso["steps"]):
            if paso["kind"] == "tool_failure":
                d.store.append_step(d.conn, tid, kind="tool_failure", tool="run_shell",
                                    args={"command": "python3 -m pytest"},
                                    error_message=paso["text"], decisive=(j == 0))
            else:
                d.store.append_step(d.conn, tid, kind="tool_use", tool="run_shell",
                                    args={"command": "sed -n 1,40p ."},
                                    result_summary=paso["text"])
        d.store.close_trajectory(d.conn, tid, result=caso["result"])
        ids.append(tid)
    return [d.store.get_trajectory(d.conn, t) for t in ids]


def armar_prompt(trayectorias, modo):
    """El prompt real del plugin, armado sobre un store desechable.

    La llamada al modelo queda **afuera** del store desechable a propósito: `HOME` está
    reapuntado a un directorio temporal mientras el contexto está abierto, y el comando del
    modelo lee su configuración de `HOME`. Consultarlo adentro lo hace salir 1 sin decir
    por qué — el hook saldría 0 igual y nadie se enteraría, que es el modo de fallo que
    este repositorio ya pagó dos veces.
    """
    from nightshift import dream
    with camino_real.StoreDesechable() as d:
        filas = sembrar(d, trayectorias)
        return dream.build_prompt(d.conn, filas, modo=modo)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--repeticiones", type=int, default=1,
                    help="la respuesta del modelo es estocástica: repetir da la tasa")
    ap.add_argument("--model", default=None)
    ap.add_argument("--grupo", help="qué grupos del fixture correr, separados por coma")
    ap.add_argument("--ideacion", default=None,
                    help="con qué medio idear: mermaid (default del plugin) o fisica."
                         " La regla de abstención vive en el cuerpo compartido, pero el"
                         " prefijo empuja — y el físico empuja a ENCONTRAR una escena, que"
                         " es justo el sesgo que la abstención existe para resistir")
    args = ap.parse_args()

    from nightshift import config, dream
    modo = args.ideacion or dream.MODO_DE_IDEACION
    if modo not in dream.MODOS_DE_IDEACION:
        raise SystemExit("--ideacion %s no existe: hay %s"
                         % (modo, ", ".join(dream.MODOS_DE_IDEACION)))
    cfg = config.load()
    if args.model:
        cfg["model_command"] = args.model.split()
    comando = dream.detect_command(cfg)
    if not comando:
        raise SystemExit("no hay modelo disponible: este experimento necesita uno")
    modelo = dream.LocalModel(comando, timeout=cfg.get("dream_timeout_seconds", 180))

    if args.repeticiones < 1:
        raise SystemExit("--repeticiones tiene que ser 1 o más: un experimento sin corrida"
                         " no es un experimento")
    print("¿dream se abstiene cuando no hay patrón?")
    print("modelo: %s" % " ".join(comando))
    print("medio de ideación: %s — la abstención se midió por primera vez con `mermaid`;" % modo)
    print("un veredicto de un medio no vale para el otro.")
    print("%d repetición(es) por grupo. Cada una es una llamada." % args.repeticiones)
    print()

    seleccion = grupos(args.grupo.split(",") if args.grupo else None)
    print("corpus: %s (%d grupo(s))" % (FIXTURE.relative_to(RAIZ), len(seleccion)))
    print()

    marcador = {"abstain": [0, 0], "pattern": [0, 0]}
    for rep in range(args.repeticiones):
        for g in seleccion:
            esperado = g["expect"]
            marcador[esperado][1] += 1
            try:
                salida = modelo.ask_json(armar_prompt(g["trajectories"], modo))
            except Exception as exc:
                print("  %-8s rep %d  ERROR: %r" % (g["id"], rep + 1, exc))
                continue
            patron = (salida or {}).get("pattern")
            se_abstuvo = not patron
            acerto = se_abstuvo if esperado == "abstain" else not se_abstuvo
            marcador[esperado][0] += bool(acerto)
            print("  %-8s rep %d  %s  %s"
                  % (g["id"], rep + 1, "OK " if acerto else "MAL",
                     "se abstuvo (pattern null)" if se_abstuvo
                     else "abstrajo: " + str(patron)[:56]))
    print()

    ok_sin, n_sin = marcador["abstain"]
    ok_con, n_con = marcador["pattern"]
    print("=" * 78)
    print("se abstuvo donde NO había patrón : %d de %d" % (ok_sin, n_sin))
    print("abstrajo  donde SÍ había patrón  : %d de %d" % (ok_con, n_con))
    print()
    if n_sin and ok_sin == n_sin and (not n_con or ok_con == n_con):
        print("SABE DECIR QUE NO. Se abstuvo donde no había nada y abstrajo donde había")
        print("algo. Es el piso que hacía falta para que sus 'sí' informen: sin esto, todo")
        print("resultado favorable de las familias A, C y D era compatible con un modelo")
        print("que encuentra patrones en cualquier cosa.")
    elif n_sin and ok_sin < n_sin and (not n_con or ok_con == n_con):
        print("NO SABE DECIR QUE NO. Encontró un patrón donde se le dieron trabajos sin")
        print("nada en común. Las familias A, C y D tienen la causa compartida ya plantada,")
        print("así que **no pueden detectar este modo de fallo**: miden la mitad favorable")
        print("de la conducta y nunca la otra.")
    elif n_con and ok_con < n_con and (not n_sin or ok_sin == n_sin):
        print("SE ABSTIENE DE MÁS. Dijo que no también donde había un mecanismo compartido:")
        print("el piso se paga con recall. Un consolidador mudo es tan inútil como uno que")
        print("inventa, y esta mitad es la que el gate de M3 no mira.")
    else:
        print("INCONSISTENTE en las dos mitades. Con este n no se distingue de azar:")
        print("repetir con --repeticiones antes de concluir nada.")
    print()
    print("n = %d por grupo. Esto no es una tasa: es un piso, y lo que mide es si el"
          % args.repeticiones)
    print("sistema **puede** decir que no.")
    print("=" * 78)


if __name__ == "__main__":
    main()
