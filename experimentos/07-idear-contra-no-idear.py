"""¿Idear compra transferencia a un síntoma que no se vio? (plan F4 / H17)

ADR-004 se aceptó con n=1 y lo dice. Desde la enmienda 0.3.7 idear es el flujo único, así
que la apuesta central del proyecto —*el dibujo de un mecanismo es invariante entre
síntomas de un modo que la prosa no lo es*— sigue sin control.

**Cómo se evita que la comparación sea circular.** Comparar "cuántas proyecciones produce
cada brazo" es trampa: `observed` no puede producir ninguna, así que el brazo ideado gana
por definición. Y preguntar si el brazo ideado engancha con sus propias proyecciones es
peor: las escribió él.

Lo que se compara es otra cosa, y tiene un conjunto **retenido** que ninguno de los dos
brazos vio: los síntomas de `cbbd7ff0` que **una persona confirmó después** (`nightshift
resolve`). La pregunta es:

> Cuando el usuario describe con sus palabras un síntoma que la sesión NO observó, ¿la
> abstracción de cada brazo lo engancha?

El brazo ideado tiene una ventaja obvia —proyectó esos síntomas— y por eso el número que
importa no es si gana, sino **cuánto** engancha el control: si `observed` engancha igual,
proyectar no compra transferencia, compra texto.

**El instrumento es la máquina.** Hasta el 2026-08-28 este archivo armaba un bolsón de
frases —`signals + pattern + decisive_signal`— y medía el enganche contra él. La cadena
real nunca matchea contra `pattern` y sí matchea contra `valid_when`: el bolsón contaba un
enganche que la máquina no produce. Desde la corrección se mide por el camino real
(`camino_real.medir`: candidata montada, `retrieve.candidates`, `retrieve.render`), y la
única definición de "engancha" es la del plugin. El diagnóstico que lo encontró está en
`08-el-techo-del-oraculo.py`.

**Y el control negativo decide igual que el retenido.** Un brazo que engancha más síntomas
retenidos comprando un prompt ajeno no compró transferencia: compró superficie. Por eso el
veredicto pide las dos cosas.

Corre una sola llamada al modelo: la del brazo de control. La salida del brazo ideado ya
está en el store.
"""

import argparse
import json
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ))
sys.path.insert(0, str(RAIZ / "experimentos"))

import camino_real                                     # noqa: E402
from nightshift import config, dream, store            # noqa: E402

# Las paráfrasis las escribe una persona, no el modelo: si las escribiera el modelo
# estaríamos midiendo cuánto se parece a sí mismo.
RETENIDOS = {
    "panel de salud con denominador cero": {
        "proyeccion": "Un panel de salud que informa cobertura perfecta cuando el "
                      "denominador es cero, sin distinguir todo bien de no hay nada.",
        "parafrasis": "el resumen dice que esta todo bien pero no conto ninguna celda",
        "veredicto": "confirmada",
    },
    "ensayo verde contra store vacio": {
        "proyeccion": "Un ensayo end to end que da verde contra un store recién creado y "
                      "vacío.",
        "parafrasis": "la corrida termina en verde y no proceso ni un solo caso",
        "veredicto": "confirmada",
    },
    "linter con lista vacia": {
        "proyeccion": "Un linter de invariantes que pasa porque su lista de archivos a "
                      "revisar quedó vacía por un patrón que no matchea nada.",
        "parafrasis": "el chequeo pasa porque su patron no encontro ningun archivo",
        "veredicto": "confirmada",
    },
}

# Control negativo: prompts que no tienen nada que ver. Sin esto, un brazo que engancha
# con todo parecería el mejor.
AJENOS = ["el certificado ssl del dominio vencio y el deploy no arranca",
          "quiero agregar paginacion a la tabla de usuarios",
          "el linter se queja de un import sin usar"]




def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--trajectory", default="cbbd7ff0")
    ap.add_argument("--model", default=None)
    ap.add_argument("--control-json", help="reusar una salida del control ya guardada")
    args = ap.parse_args()

    conn = store.connect()
    fila = conn.execute("SELECT * FROM trajectories WHERE id LIKE ?",
                        (args.trajectory + "%",)).fetchone()
    if fila is None or not fila["abstraction_json"]:
        raise SystemExit("no encuentro una candidata que empiece con %s" % args.trajectory)

    ideado = json.loads(fila["abstraction_json"])
    proyectadas = [p["text"] for p in store.projections_of(conn, fila["id"])]

    if args.control_json:
        control = json.loads(Path(args.control_json).read_text(encoding="utf-8"))
    else:
        cfg = config.load()
        if args.model:
            cfg["model_command"] = args.model.split()
        comando = dream.detect_command(cfg)
        if not comando:
            raise SystemExit("no hay modelo disponible: este experimento necesita uno")
        modelo = dream.LocalModel(comando, timeout=cfg.get("dream_timeout_seconds", 180))
        prompt = dream.build_prompt(conn, [fila], ideate=False)     # el brazo de control
        print("llamando al modelo para el brazo de CONTROL (sin idear)…", file=sys.stderr)
        control = modelo.ask_json(prompt)
        Path("experimentos/salidas/07-control-observed.json").write_text(
            json.dumps(control, indent=2, ensure_ascii=False), encoding="utf-8")

    conn.close()

    retenidos = [(nombre, caso["parafrasis"]) for nombre, caso in RETENIDOS.items()]
    brazos = [("control", control, []), ("ideado", ideado, proyectadas)]
    marcadores = {n: camino_real.medir(a, p, retenidos, AJENOS) for n, a, p in brazos}

    print("corpus: la trayectoria `%s` (%s)" % (fila["id"][:8], fila["task_type"]))
    print("brazo ideado : %d proyecciones. brazo control: 0 (no puede producirlas)."
          % len(proyectadas))
    print("medido por el camino real: candidata montada, `candidates`, `render`.")
    print()
    print("%-38s %-9s %-9s" % ("síntoma retenido (paráfrasis humana)", "control", "ideado"))
    print("-" * 60)
    for i, (nombre, _) in enumerate(retenidos):
        fila_c = marcadores["control"]["detalle"][i]
        fila_i = marcadores["ideado"]["detalle"][i]
        print("%-38s %-9s %-9s" % (nombre[:38],
                                   "SI" if fila_c["engancha"] else "no",
                                   "SI" if fila_i["engancha"] else "no"))
    print("-" * 60)
    print("%-38s %d de %d   %d de %d"
          % ("rankea", marcadores["control"]["retenidos"], len(retenidos),
             marcadores["ideado"]["retenidos"], len(retenidos)))
    print("%-38s %d de %d   %d de %d"
          % ("LLEGA al agente", marcadores["control"]["retenidos_llegan"], len(retenidos),
             marcadores["ideado"]["retenidos_llegan"], len(retenidos)))
    print()
    sin_compuerta = [n for n, _ in retenidos
                     if not camino_real.compuerta(dict(retenidos)[n])[0]]
    if sin_compuerta:
        print("%d de %d síntomas retenidos clasifican como `general`, así que"
              % (len(sin_compuerta), len(retenidos)))
        print("`on_user_prompt_submit` sale antes de rankear y no inyectan nada en una")
        print("sesión real, por alto que rankeen. Ver LATER.md, la compuerta del")
        print("clasificador. La fila de arriba es el ranking; la de abajo, lo que llega.")
        print()
    print("control negativo (%d prompts ajenos): control %d, ideado %d — cualquier valor"
          % (len(AJENOS), marcadores["control"]["ajenos"], marcadores["ideado"]["ajenos"]))
    print("distinto de 0 invalida el enganche del brazo que lo tenga.")
    print("  y de ésos, LLEGAN al agente: control %d, ideado %d"
          % (marcadores["control"]["ajenos_llegan"], marcadores["ideado"]["ajenos_llegan"]))
    for nombre in ("control", "ideado"):
        for d in marcadores[nombre]["detalle"]:
            if d["clase"] == "ajeno" and d["engancha"]:
                print("  %-8s enganchó `%s` (%s)" % (nombre, d["prompt"][:44], d["motivos"]))
    print()
    print("n = 1 corpus, %d síntomas retenidos. Esto no cierra la apuesta de ADR-004."
          % len(retenidos))

    gana = (marcadores["ideado"]["retenidos"] > marcadores["control"]["retenidos"])
    limpio = marcadores["ideado"]["ajenos"] == 0
    print()
    if gana and limpio:
        print("RESULTADO: idear compró transferencia y no compró falsos positivos.")
    elif gana:
        print("RESULTADO: idear enganchó %d síntoma(s) retenido(s) más que el control, y lo"
              % (marcadores["ideado"]["retenidos"] - marcadores["control"]["retenidos"]))
        print("pagó con %d prompt(s) ajeno(s). Más superficie engancha más de las dos cosas:"
              % marcadores["ideado"]["ajenos"])
        print("mientras el control negativo no dé 0, la transferencia extra no se puede")
        print("separar de la indiscriminación. NO alcanza para sostener ADR-004.")
    else:
        print("RESULTADO: idear NO compró transferencia en este corpus. Queda escrito")
        print("igual — `experimentos/` existe para los resultados que no favorecen al")
        print("plugin, y sin ésos los demás no valen nada.")



if __name__ == "__main__":
    main()
