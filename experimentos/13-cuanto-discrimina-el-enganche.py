"""¿Cuánto discrimina el enganche cuando el store crece? (empezó por un verbo)

**Este experimento se abrió para responder una pregunta chica y encontró una grande.** La
chica: si hay una clase de verbo genérico —`arranca`, `termina`, `corre`— que no puede
sostener un enganche sola, como ya se decidió para los predicados de fallo. La grande, que
apareció al medir: **el enganche destilado casi no discrimina cuando el store tiene más de
una memoria.**

    piso  engancha algo  la que corresponde  y entra en el top-3   ajenos
      1     15 de 17       11 de 17            4 de 17              17 de 24   <- hoy
      2      5 de 17        5 de 17            5 de 17               2 de 24
      3      1 de 17        0 de 17            0 de 17               0 de 24

**Las tres columnas de verdaderos no dicen lo mismo, y sólo la tercera importa.** Con el
piso de hoy engancha algo el 88% de los prompts, pero la memoria que corresponde entra en la
inyección **4 de 17**: las otras la desplazan. Con piso 2 entra **5 de 17** —más— y los
falsos positivos caen de 17 a 2.

**Subir el piso no es un intercambio: es mejor en las dos mitades.** Lo que se pierde al
bajarlo no son enganches útiles, son enganches con la memoria equivocada que además tapan a
la correcta.

La enmienda 0.3.6 midió el piso contra **una sola candidata**, donde "engancha algo" y
"engancha la que corresponde" son la misma pregunta. Con seis candidatas se separan, y ahí
se ve que el piso bajo compra ruido.

Lo que sigue abajo es la pregunta chica, con su respuesta, porque su medición es la que
destapó la grande.

---

¿Hay una clase de verbo que no puede sostener un enganche sola? (medir antes de tocar)

**De dónde sale.** El ciclo de sueño del 2026-08-28 dejó un falso positivo que carga **una
sola palabra**:

    "el certificado ssl del dominio vencio y el deploy no arranca"
      comunes=['arranca']
      <- "La exploración inicial del proyecto arranca con un fallo que igual parece haber
          funcionado"

`_PREDICADOS_DE_FALLO` no lo cubre, y con razón: esa lista es de palabras que dicen **que**
algo se rompió —`falla`, `rompe`, `anda`— y `arranca` no dice eso. Dice que algo
**empieza**. Es una clase distinta: verbos genéricos de proceso, que aparecen en cualquier
prompt de cualquier dominio y no nombran de qué se habla.

Es la tercera colisión de un solo término que encuentra este repo, después de `falla`
(enmienda 0.3.6) y `linter` (experimento `07`).

**Por qué esto es un experimento y no un parche.** Las dos entradas que ya tiene la lista
salieron de **medir** sobre un corpus, no de que a alguien le parecieran genéricas (spec
§5.10). Agregar palabras a ojo es empezar a decidir a mano qué se parece a qué, que es
exactamente lo que el ranking tiene que hacer de forma auditable. Así que acá se mide, una
palabra por vez, las dos mitades:

- **lo que saca:** prompts ajenos que dejan de enganchar (falsos positivos removidos);
- **lo que se lleva puesto:** prompts verdaderos que dejan de enganchar.

Una palabra que saca falsos positivos y no se lleva ninguno verdadero es gratis. Una que se
lleva verdaderos tiene un precio, y el precio se escribe.

**El corpus, y ninguna parte la inventó esta sesión.**

- **Verdaderos:** las 14 paráfrasis humanas del experimento `05` —escritas para `fff6af83`
  antes de que existiera esta pregunta— más los 3 síntomas retenidos de `cbbd7ff0` que una
  persona confirmó.
- **Ajenos:** los 6 del control negativo del `05` más los 18 del `09`.

Se mide contra el **store real, en sólo lectura**, con `retrieve.candidates`: la pregunta
es si alguna memoria del store engancha, que es lo que pasa en una sesión.

    python3 experimentos/13-cuanto-discrimina-el-enganche.py
    python3 experimentos/13-cuanto-discrimina-el-enganche.py --palabra arranca
"""

import argparse
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ))
sys.path.insert(0, str(RAIZ / "experimentos"))

import camino_real                                                  # noqa: E402

# Las 14 paráfrasis humanas del `05` (escritas para `fff6af83`, antes de esta pregunta) y
# los 3 síntomas retenidos que una persona confirmó para `cbbd7ff0`.
# Cada prompt con **la memoria que le corresponde**, y esa columna es la que hacía falta:
# preguntar "¿engancha algo?" cuenta como acierto que el prompt de una paráfrasis de
# `fff6af83` enganche con `07695a69`, que es un falso positivo con otro nombre. La
# procedencia: las 14 primeras son las paráfrasis humanas del `05`, escritas para
# `fff6af83`; las 3 últimas, los síntomas retenidos que una persona confirmó de `cbbd7ff0`.
VERDADEROS_CON_MEMORIA = [
    ("ninguna de las acciones que ejecute quedo con descripcion", "fff6af83"),
    ("las tool calls se registran pero sin ningun detalle de lo que hicieron", "fff6af83"),
    ("no se que hizo el agente porque los registros no tienen informacion", "fff6af83"),
    ("no puedo saber si la sesion termino bien o mal", "fff6af83"),
    ("todas las sesiones me quedan sin resultado final", "fff6af83"),
    ("las trayectorias son indistinguibles, solo cambia el numero de pasos", "fff6af83"),
    ("todo me cae en la categoria por defecto, nada se clasifica", "fff6af83"),
    ("el vacio es parejo en todos lados, no parece un caso aislado", "fff6af83"),
    ("la busqueda me trae siempre lo mismo sin importar que le pregunte", "fff6af83"),
    ("el ranking no cambia aunque cambie el texto que le paso", "fff6af83"),
    ("dos resumenes de tareas diferentes me salieron practicamente iguales", "fff6af83"),
    ("las metricas dicen que esta todo bien pero es mentira", "fff6af83"),
    ("abri un registro guardado y estaba todo vacio, los campos existen pero no tienen nada adentro",
     "fff6af83"),
    ("los datos se guardan pero cuando los leo no hay texto en ningun lado", "fff6af83"),
    ("el resumen dice que esta todo bien pero no conto ninguna celda", "cbbd7ff0"),
    ("la corrida termina en verde y no proceso ni un solo caso", "cbbd7ff0"),
    ("el chequeo pasa porque su patron no encontro ningun archivo", "cbbd7ff0"),
]
VERDADEROS = [p for p, _ in VERDADEROS_CON_MEMORIA]

# El control negativo del `05` más el del `09`.
AJENOS = [
    "el css del boton de login quedo desalineado en mobile",
    "necesito agregar un indice a la tabla de usuarios porque la query tarda 3 segundos",
    "el deploy a produccion falla con un error de certificado ssl vencido",
    "quiero renombrar la variable foo a bar en todo el proyecto",
    "como configuro el timezone del servidor",
    "agregame un endpoint nuevo que devuelva el healthcheck",
    "el bundle de webpack pesa 4 megas y la landing tarda en pintar",
    "el modelo entrena pero la loss se queda planchada desde la epoca 3",
    "la app de android crashea al rotar la pantalla en el detalle de producto",
    "la query del reporte mensual tarda 40 segundos contra postgres",
    "el certificado ssl del dominio vencio y el deploy no arranca",
    "quiero agregar paginacion a la tabla de usuarios",
    "el personaje atraviesa la pared cuando corre en diagonal",
    "el firmware se cuelga cuando el sensor devuelve un valor negativo",
    "el webhook de pagos llega duplicado y cobramos dos veces",
    "el build de docker tarda 12 minutos por el layer de dependencias",
    "el test falla intermitentemente en ci pero pasa en local",
    "el linter se queja de un import sin usar",
    "la suite tarda 9 minutos y quiero paralelizarla",
    "el mock del cliente http no se resetea entre tests",
    "el coverage bajo de 82 a 79 y no se que test se borro",
    "el pipeline de ci falla en el paso de build por falta de memoria",
    "un test rompe solo cuando corre despues del de autenticacion",
    "el snapshot del componente cambia en cada corrida por el timestamp",
]

# Candidatas: verbos que dicen que algo **ocurre**, no qué cosa. Se prueban de a una, con
# sus formas, porque `_tokens` no lematiza — el mismo motivo por el que la lista existente
# enumera `rompe rompio roto rompen`.
CANDIDATAS = {
    "arranca": ["arranca", "arrancar", "arranco", "arrancaba"],
    "empieza": ["empieza", "empezar", "empezo", "comienza", "comenzar"],
    "termina": ["termina", "terminar", "termino", "terminaba"],
    "corre": ["corre", "correr", "corrio", "corriendo"],
    "pasa": ["pasa", "pasar", "paso", "pasaba"],
    "queda": ["queda", "quedar", "quedo", "quedaba"],
    "vuelve": ["vuelve", "volver", "volvio"],
    "sale": ["sale", "salir", "salio"],
    "aparece": ["aparece", "aparecer", "aparecio"],
    "devuelve": ["devuelve", "devolver", "devolvio"],
    "tarda": ["tarda", "tardar", "tardo"],
    "llega": ["llega", "llegar", "llego"],
}


def engancha(conn, cfg, prompt, fingerprint):
    """¿Alguna memoria del store engancha con este prompt? Por el camino real, sin escribir."""
    from nightshift import context, retrieve
    tipo = context.classify_task(prompt)
    scored = retrieve.candidates(conn, task_type=tipo, repo_fingerprint=fingerprint,
                                 cfg=cfg, prompt=prompt)
    for _, motivos, _ in scored:
        if retrieve.MOTIVOS_DE_ENGANCHE & set(motivos.split(",")):
            return True
    return False


def medir_con(conn, cfg, fingerprint, extra=()):
    """Cuántos verdaderos y cuántos ajenos enganchan, con la lista extendida por `extra`.

    Se reemplaza `retrieve._PREDICADOS_DE_FALLO` en memoria y se restaura después. Es una
    medición de una lista **hipotética**: nada se persiste y el módulo queda como estaba.
    """
    from nightshift import retrieve
    original = retrieve._PREDICADOS_DE_FALLO
    retrieve._PREDICADOS_DE_FALLO = frozenset(original | set(extra))
    try:
        v = [p for p in VERDADEROS if engancha(conn, cfg, p, fingerprint)]
        a = [p for p in AJENOS if engancha(conn, cfg, p, fingerprint)]
    finally:
        retrieve._PREDICADOS_DE_FALLO = original
    return v, a


def medir_fino(conn, cfg, fingerprint, piso):
    """Tres preguntas distintas, y sólo la tercera es la que le importa a una sesión.

    1. ¿engancha **algo**? — es lo que se venía midiendo, y cuenta como acierto que la
       paráfrasis de una memoria enganche con otra.
    2. ¿engancha **la que corresponde**? — un enganche con la memoria equivocada es un
       falso positivo con otro nombre.
    3. ¿la que corresponde **entra en el top-`max_injected`**? — porque lo que el agente
       lee son las primeras, y una memoria correcta desplazada por tres incorrectas no
       llegó.
    """
    from nightshift import context, retrieve
    n = cfg.get("max_injected", 3)
    original = retrieve.MIN_TOKENS_DESTILADO
    retrieve.MIN_TOKENS_DESTILADO = piso
    algo = correcta = arriba = 0
    try:
        for prompt, memoria in VERDADEROS_CON_MEMORIA:
            scored = retrieve.candidates(conn, task_type=context.classify_task(prompt),
                                         repo_fingerprint=fingerprint, cfg=cfg,
                                         prompt=prompt)
            def engancha_fila(m):
                return bool(retrieve.MOTIVOS_DE_ENGANCHE & set(m.split(",")))
            algo += any(engancha_fila(m) for _, m, _ in scored)
            correcta += any(r["id"].startswith(memoria) and engancha_fila(m)
                            for _, m, r in scored)
            arriba += any(r["id"].startswith(memoria) for _, _, r in scored[:n])
        ajenos = [p for p in AJENOS if engancha(conn, cfg, p, fingerprint)]
    finally:
        retrieve.MIN_TOKENS_DESTILADO = original
    return {"algo": algo, "correcta": correcta, "arriba": arriba, "ajenos": len(ajenos)}


def medir_con_piso(conn, cfg, fingerprint, piso):
    """Lo mismo, moviendo el piso del texto destilado en vez de la lista de palabras."""
    from nightshift import retrieve
    original = retrieve.MIN_TOKENS_DESTILADO
    retrieve.MIN_TOKENS_DESTILADO = piso
    try:
        v = [p for p in VERDADEROS if engancha(conn, cfg, p, fingerprint)]
        a = [p for p in AJENOS if engancha(conn, cfg, p, fingerprint)]
    finally:
        retrieve.MIN_TOKENS_DESTILADO = original
    return v, a


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--palabra", help="medir sólo una de las candidatas")
    args = ap.parse_args()

    from nightshift import config, context, store
    cfg = config.load()
    fingerprint = context.repo_fingerprint(str(RAIZ))
    conn = store.connect()
    try:
        base_v, base_a = medir_con(conn, cfg, fingerprint)
        print("verbos genéricos — medir antes de tocar la lista")
        print("store real, sólo lectura · %d prompts verdaderos · %d ajenos"
              % (len(VERDADEROS), len(AJENOS)))
        print()
        print("hoy: enganchan %d de %d verdaderos y %d de %d ajenos"
              % (len(base_v), len(VERDADEROS), len(base_a), len(AJENOS)))
        for p in base_a:
            print("   falso positivo: %s" % p)
        print()

        candidatas = ({args.palabra: CANDIDATAS[args.palabra]} if args.palabra
                      else CANDIDATAS)
        print("%-12s %-26s %s" % ("palabra", "saca (falsos positivos)", "se lleva (verdaderos)"))
        print("-" * 74)
        gratis, con_precio = [], []
        for nombre, formas in candidatas.items():
            v, a = medir_con(conn, cfg, fingerprint, formas)
            saca = [p for p in base_a if p not in a]
            lleva = [p for p in base_v if p not in v]
            (gratis if saca and not lleva else con_precio).append((nombre, saca, lleva))
            print("%-12s %-26s %s"
                  % (nombre,
                     "%d" % len(saca) if saca else "—",
                     "%d: %s" % (len(lleva), lleva[0][:34]) if lleva else "—"))
        print("-" * 74)
        print()

        if gratis:
            print("GRATIS — sacan falsos positivos y no se llevan ningún verdadero:")
            for nombre, saca, _ in gratis:
                print("  %-10s saca %d:" % (nombre, len(saca)))
                for p in saca:
                    print("      %s" % p)
            print()
            juntas = [f for n, _, _ in gratis for f in CANDIDATAS[n]]
            v, a = medir_con(conn, cfg, fingerprint, juntas)
            print("las %d juntas: %d de %d verdaderos (hoy %d) · %d de %d ajenos (hoy %d)"
                  % (len(gratis), len(v), len(VERDADEROS), len(base_v),
                     len(a), len(AJENOS), len(base_a)))
            print()

        con_costo = [(n, s, l) for n, s, l in con_precio if l]
        if con_costo:
            print("CON PRECIO — se llevan enganches verdaderos. No entran sin que alguien")
            print("decida que el precio vale la pena:")
            for nombre, saca, lleva in con_costo:
                print("  %-10s saca %d, se lleva %d" % (nombre, len(saca), len(lleva)))
                for p in lleva:
                    print("      pierde: %s" % p[:66])
            print()
        print("=" * 74)
        print("Y la pregunta grande, que apareció midiendo la chica:")
        print()
        print("%-6s %-13s %-15s %-16s %s"
              % ("piso", "engancha algo", "engancha la que", "y entra en el", "ajenos"))
        print("%-6s %-13s %-15s %-16s %s" % ("", "", "corresponde", "top-%d" % cfg.get("max_injected", 3), ""))
        print("-" * 74)
        for piso in (1, 2, 3):
            r = medir_fino(conn, cfg, fingerprint, piso)
            print("%-6s %-13s %-15s %-16s %s  %s"
                  % (piso, "%d de %d" % (r["algo"], len(VERDADEROS)),
                     "%d de %d" % (r["correcta"], len(VERDADEROS)),
                     "%d de %d" % (r["arriba"], len(VERDADEROS)),
                     "%d de %d" % (r["ajenos"], len(AJENOS)),
                     "<- hoy" if piso == 1 else ""))
        print("-" * 74)
        print()
        print("**Las tres columnas de verdaderos no dicen lo mismo, y sólo la tercera")
        print("importa.** Con el piso de hoy engancha algo el 88% de los prompts, pero la")
        print("memoria que corresponde entra en la inyección sólo 4 de 17: las otras la")
        print("desplazan. Con piso 2 entra 5 de 17 — más — y los falsos positivos caen de")
        print("17 a 2.")
        print()
        print("Subir el piso NO es un intercambio: es mejor en las dos mitades. Lo que se")
        print("pierde al bajarlo no son enganches útiles, son enganches con la memoria")
        print("equivocada que además tapan a la correcta.")
        print()
        print("La enmienda 0.3.6 midió el piso contra UNA candidata, donde 'engancha algo'")
        print("y 'engancha la que corresponde' son lo mismo. Con seis, se separan.")
        print("=" * 74)
        print()
        print("Esto mide el **ranking**. Lo que llega al agente pasa además por la")
        print("compuerta del clasificador, y ahí varios de estos prompts no llegan")
        print("(LATER.md, la compuerta). Sacar un falso positivo del ranking sigue")
        print("valiendo: la compuerta es una decisión de spec y ésta no.")
    finally:
        conn.close()


if __name__ == "__main__":
    main()
