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

Corre una sola llamada al modelo: la del brazo de control. La salida del brazo ideado ya
está en el store.
"""

import argparse
import json
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ))

from nightshift import config, dream, retrieve, store   # noqa: E402

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


def frases_de(abstraccion):
    """Lo destilado de una abstracción: es contra esto que se mide el enganche."""
    frases = list(abstraccion.get("signals") or [])
    if abstraccion.get("pattern"):
        frases.append(abstraccion["pattern"])
    if abstraccion.get("decisive_signal"):
        frases.append(abstraccion["decisive_signal"])
    return frases


def engancha(prompt, frases):
    return bool(retrieve._enganche(retrieve._tokens(prompt), frases,
                                   retrieve.MIN_TOKENS_DESTILADO))


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

    frases_control = frases_de(control)
    frases_ideado = frases_de(ideado)

    print("corpus: la trayectoria `%s` (%s)" % (fila["id"][:8], fila["task_type"]))
    print("brazo ideado : %d frase(s) destiladas + %d proyecciones"
          % (len(frases_ideado), len(proyectadas)))
    print("brazo control: %d frase(s) destiladas + 0 proyecciones (no puede producirlas)"
          % len(frases_control))
    print()
    print("%-38s %-9s %-9s" % ("síntoma retenido (paráfrasis humana)", "control", "ideado"))
    print("-" * 60)
    marcador = {"control": 0, "ideado": 0}
    for nombre, caso in RETENIDOS.items():
        c = engancha(caso["parafrasis"], frases_control)
        i = engancha(caso["parafrasis"], frases_ideado + proyectadas)
        marcador["control"] += bool(c)
        marcador["ideado"] += bool(i)
        print("%-38s %-9s %-9s" % (nombre[:38], "SI" if c else "no", "SI" if i else "no"))
    print("-" * 60)
    print("%-38s %d de %d   %d de %d" % ("engancha", marcador["control"], len(RETENIDOS),
                                         marcador["ideado"], len(RETENIDOS)))
    print()
    falsos = {"control": sum(engancha(p, frases_control) for p in AJENOS),
              "ideado": sum(engancha(p, frases_ideado + proyectadas) for p in AJENOS)}
    print("control negativo (%d prompts ajenos): control %d, ideado %d — cualquier valor"
          % (len(AJENOS), falsos["control"], falsos["ideado"]))
    print("distinto de 0 invalida el enganche del brazo que lo tenga.")
    print()
    print("n = 1 corpus, %d síntomas retenidos. Esto no cierra la apuesta de ADR-004."
          % len(RETENIDOS))
    if marcador["ideado"] <= marcador["control"]:
        print()
        print("RESULTADO: idear NO compró transferencia en este corpus. Queda escrito")
        print("igual — `experimentos/` existe para los resultados que no favorecen al")
        print("plugin, y sin ésos los demás no valen nada.")
    conn.close()


if __name__ == "__main__":
    main()
