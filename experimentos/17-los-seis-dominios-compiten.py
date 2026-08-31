"""Los seis dominios, medidos: ¿la memoria de cada uno llega el día que hace falta?

Lee los suenios que dejó `16-los-suenios-de-los-seis-dominios.py` y los hace pasar por el
camino real —`retrieve.candidates` + `retrieve.render`, con la compuerta de
`context.classify_task` en el medio—, que es literalmente lo que corre el hook.

Tres marcadores, y hay que decir cuál se cita:

- **E1(d) · dominio solo.** La candidata del dominio, sola en un store: ¿enganchan sus dos
  síntomas retenidos —terceras caras del mismo mecanismo, escritas y commiteadas antes de
  que el modelo consolidara— y se quedan afuera los diez ajenos?
- **E2(d) · la precondición.** Qué devolvió el contraste de ADR-005 sobre la alternativa
  descartada, al lado de la precondición que el pre-registro esperaba. **El script no
  juzga el parecido**: imprime las dos y la comparación la hace una persona.
- **E3 · los seis juntos.** Las seis candidatas en un solo store y los doce síntomas
  preguntando: ¿cada uno encuentra el dominio del que salió?

No llama a ningún modelo y no toca el store real.

**El asterisco, que va acá y no al final.** Las trayectorias, los retenidos y los ajenos
los escribió la misma mano. Esto es un **techo de autor**: dice qué puede dar la cadena
con material armado para ser separable, y nunca que la memoria sirva en un SOC, en una
guardia o en una planta.
"""

import argparse
import json
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ))
sys.path.insert(0, str(RAIZ / "experimentos"))

import camino_real                                           # noqa: E402
import casos_de_dominio                                      # noqa: E402

SALIDAS = RAIZ / "experimentos" / "salidas" / "dominios"


def cargar(slug):
    ruta = SALIDAS / ("%s.json" % slug)
    if not ruta.exists():
        return None
    with open(ruta, encoding="utf-8") as fh:
        return json.load(fh)


def montar_suenio(d, suenio):
    """La candidata soñada, montada por el camino real. Devuelve el id, o None."""
    candidatas = suenio.get("candidatas") or []
    if not candidatas:
        return None
    c = candidatas[0]
    abstraccion = dict(c["abstraction"])
    abstraccion["valid_when"] = [v.get("condition") if isinstance(v, dict) else v
                                 for v in (c.get("valid_when") or [])]
    return camino_real.montar(d, abstraccion, c.get("projected_signals") or [],
                              physical_scene=c.get("physical_scene"),
                              logogram=c.get("logogram"))


def e1(slug, suenio):
    """El dominio solo contra sus dos retenidos y los diez ajenos."""
    caso = casos_de_dominio.por_slug(slug)
    candidatas = suenio.get("candidatas") or []
    if not candidatas:
        return None
    c = candidatas[0]
    abstraccion = dict(c["abstraction"])
    abstraccion["valid_when"] = [v.get("condition") if isinstance(v, dict) else v
                                 for v in (c.get("valid_when") or [])]
    ajenos = [p for _, p in casos_de_dominio.retenidos_ajenos(slug)]
    marcador = camino_real.medir(abstraccion, c.get("projected_signals") or [],
                                 caso["retenidos"], ajenos)
    marcador["proyecciones"] = len(c.get("projected_signals") or [])
    marcador["escena"] = bool(c.get("physical_scene"))
    marcador["logograma"] = c.get("logogram")
    return marcador


def e1_semantico(slug, suenio, comando):
    """El mismo E1, con el fallback semántico enchufado (ADR-003, enmienda 2026-08-29).

    Existe porque el proyecto ya construyó una salida para el modo de falla que E1 mide
    —las palabras no coinciden aunque el mecanismo sea el mismo— y esa salida está
    **apagada por default**. Medirla es más honesto que suponerla: la nota de calibración
    de `config.py` dice que el coseno separa sinónimos de registro parecido y NO separa
    síntoma contra mecanismo abstracto (0.24-0.28, por debajo de los ajenos), que es
    exactamente el par que este experimento tiene entre manos.

    No usa `camino_real.medir` porque ése carga la config él solo. Usa las otras tres
    piezas del mismo módulo —`montar`, `compuerta`, `llega`— así que el camino sigue
    siendo el real: lo único que cambia es una clave de config.
    """
    from nightshift import config

    caso = casos_de_dominio.por_slug(slug)
    candidatas = suenio.get("candidatas") or []
    if not candidatas:
        return None
    c = candidatas[0]
    abstraccion = dict(c["abstraction"])
    abstraccion["valid_when"] = [v.get("condition") if isinstance(v, dict) else v
                                 for v in (c.get("valid_when") or [])]
    ajenos = [("AJENO", p) for _, p in casos_de_dominio.retenidos_ajenos(slug)]

    with camino_real.StoreDesechable() as d:
        camino_real.montar(d, abstraccion, c.get("projected_signals") or [],
                           physical_scene=c.get("physical_scene"),
                           logogram=c.get("logogram"))
        cfg = dict(config.load())
        cfg["embedding_command"] = comando
        marcador = {"retenidos": 0, "ajenos": 0, "detalle": []}
        for clase, items in (("retenido", caso["retenidos"]), ("ajeno", ajenos)):
            for etiqueta, prompt in items:
                _, tipo = camino_real.compuerta(prompt)
                _, engancha, motivos = camino_real.llega(d, cfg, prompt, tipo=tipo)
                marcador[clase + "s"] += bool(engancha)
                marcador["detalle"].append({"clase": clase, "etiqueta": etiqueta,
                                            "prompt": prompt, "engancha": engancha,
                                            "motivos": motivos})
    return marcador


def e3(suenios):
    """Los seis en un store. ¿Cada síntoma encuentra el dominio del que salió?"""
    from nightshift import config, retrieve

    with camino_real.StoreDesechable() as d:
        de_quien = {}
        for slug, suenio in suenios.items():
            tid = montar_suenio(d, suenio)
            if tid:
                de_quien[tid] = slug
        if not de_quien:
            return None
        cfg = config.load()
        filas = []
        for caso in casos_de_dominio.CASOS:
            if caso["slug"] not in de_quien.values():
                continue
            for etiqueta, prompt in caso["retenidos"]:
                _, tipo = camino_real.compuerta(prompt)
                scored = retrieve.candidates(d.conn, task_type=tipo,
                                             repo_fingerprint=camino_real.REPO,
                                             cfg=cfg, prompt=prompt)
                _, elegidas = retrieve.render(
                    d.conn, scored, max_injected=cfg.get("max_injected", 3),
                    native_memory=None, task_type=tipo,
                    repo_fingerprint=camino_real.REPO)
                elegidos = {row["id"] for _, _, row in elegidas}
                enganchan = [de_quien[row["id"]] for _, motivos, row in scored
                             if retrieve.MOTIVOS_DE_ENGANCHE
                             & set((motivos or "").split(","))]
                filas.append({
                    "dominio": caso["slug"], "etiqueta": etiqueta, "prompt": prompt,
                    "propio_engancha": caso["slug"] in enganchan,
                    "ajenos_que_enganchan": [s for s in enganchan
                                             if s != caso["slug"]],
                    # ¿El propio quedó entre los tres que el hook inyecta?
                    "propio_elegido": any(t for t, s in de_quien.items()
                                          if s == caso["slug"] and t in elegidos),
                    "primero": enganchan[0] if enganchan else None,
                })
        return filas


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--semantico", nargs="*", default=None, metavar="ARG",
                    help="repite E1 con el fallback semántico enchufado. Sin argumentos "
                         "usa `sh tools/embed-ollama.sh`, que es el de referencia")
    args = ap.parse_args()
    comando_semantico = None
    if args.semantico is not None:
        comando_semantico = args.semantico or ["sh", str(RAIZ / "tools" / "embed-ollama.sh")]

    suenios, faltan = {}, []
    for caso in casos_de_dominio.CASOS:
        s = cargar(caso["slug"])
        if s and not s.get("error"):
            suenios[caso["slug"]] = s
        else:
            faltan.append(caso["slug"])

    print("Los seis dominios del README, medidos por el camino real.")
    print("Material de autor: esto es un TECHO, no transferencia.")
    print()
    if faltan:
        print("sin suenio (corré primero el 16): %s" % ", ".join(faltan))
        print()
    if not suenios:
        return 1

    # --------------------------------------------------------------- E1
    print("== E1 · cada dominio solo: sus 2 retenidos, y 10 ajenos ==")
    print()
    print("%-26s %-6s %-9s %-9s %-7s" % ("dominio", "proy.", "engancha", "llega",
                                         "ajenos"))
    print("-" * 62)
    totales = {"engancha": 0, "llega": 0, "ajenos": 0, "posibles": 0}
    for slug, suenio in suenios.items():
        m = e1(slug, suenio)
        if not m:
            print("%-26s  sin candidata" % slug)
            continue
        print("%-26s %-6d %-9s %-9s %-7d" % (
            slug, m["proyecciones"],
            "%d de 2" % m["retenidos"], "%d de 2" % m["retenidos_llegan"],
            m["ajenos"]))
        for det in m["detalle"]:
            if det["clase"] == "retenido" and not det["engancha"]:
                print("      no engancha: `%s`" % det["prompt"][:52])
            if det["clase"] == "ajeno" and det["engancha"]:
                print("      FALSO POSITIVO: `%s` (%s)"
                      % (det["prompt"][:44], det["motivos"]))
        totales["engancha"] += m["retenidos"]
        totales["llega"] += m["retenidos_llegan"]
        totales["ajenos"] += m["ajenos"]
        totales["posibles"] += 2
    print("-" * 62)
    print("engancha %d de %d · llega %d de %d · ajenos %d"
          % (totales["engancha"], totales["posibles"],
             totales["llega"], totales["posibles"], totales["ajenos"]))
    print()

    if comando_semantico:
        print("== E1-bis · el mismo E1 con el fallback semántico enchufado ==")
        print()
        print("Está apagado por default. La calibración del propio proyecto dice que el")
        print("coseno separa sinónimos y NO separa síntoma contra mecanismo abstracto.")
        print()
        print("%-26s %-9s %-7s" % ("dominio", "engancha", "ajenos"))
        print("-" * 46)
        bis = {"engancha": 0, "ajenos": 0}
        for slug, suenio in suenios.items():
            m = e1_semantico(slug, suenio, comando_semantico)
            if not m:
                continue
            print("%-26s %-9s %-7d" % (slug, "%d de 2" % m["retenidos"], m["ajenos"]))
            bis["engancha"] += m["retenidos"]
            bis["ajenos"] += m["ajenos"]
            for det in m["detalle"]:
                if "semantic_match" in (det["motivos"] or ""):
                    print("      por coseno: [%s] `%s`"
                          % (det["clase"], det["prompt"][:44]))
        print("-" * 46)
        print("engancha %d de %d · ajenos %d"
              % (bis["engancha"], 2 * len(suenios), bis["ajenos"]))
        print()

    # --------------------------------------------------------------- E2
    print("== E2 · la alternativa descartada, con su precondición ==")
    print()
    for slug, suenio in suenios.items():
        con = [x for x in suenio.get("contrastes") or [] if x.get("contrast")]
        print("▸ %s" % slug)
        if not con:
            print("   el contraste no devolvió nada")
            print()
            continue
        contraste = con[0]["contrast"]
        print("   cambió:   %s" % (contraste.get("changed") or "—"))
        print("   compró:   %s" % (contraste.get("bought") or "—"))
        for cond in contraste.get("old_valid_when") or ["(ninguna)"]:
            print("   la vieja tenía razón: %s" % cond)
        print("   esperado (pre-registro): %s" % suenio["precondicion_esperada"])
        print()
    print("El parecido entre las dos últimas líneas lo juzga una persona. Un script que")
    print("lo puntúe estaría inventando un umbral, y los umbrales los fija Matías.")
    print()

    # --------------------------------------------------------------- E3
    print("== E3 · los seis compitiendo en un solo store ==")
    print()
    filas = e3(suenios)
    if not filas:
        return 1
    print("%-26s %-24s %-9s %-7s" % ("dominio", "síntoma retenido", "propio", "ajenos"))
    print("-" * 70)
    for f in filas:
        print("%-26s %-24s %-9s %-7s" % (
            f["dominio"], f["etiqueta"][:24],
            "SI" if f["propio_engancha"] else "no",
            ", ".join(f["ajenos_que_enganchan"]) or "—"))
    print("-" * 70)
    propios = sum(f["propio_engancha"] for f in filas)
    elegidos = sum(f["propio_elegido"] for f in filas)
    cruces = sum(bool(f["ajenos_que_enganchan"]) for f in filas)
    print("el propio engancha: %d de %d" % (propios, len(filas)))
    print("el propio queda entre los inyectados: %d de %d" % (elegidos, len(filas)))
    print("síntomas que además enganchan otro dominio: %d de %d" % (cruces, len(filas)))
    print()
    print("Todo lo de arriba lo escribió la misma mano. Es un techo de autor: dice qué")
    print("puede dar la cadena con material separable, nunca que la memoria sirva.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
