"""¿El enganche por síntoma sobrevive a que el usuario lo diga con otras palabras?

**El hueco que midió.** La spec §5.10 se escribió midiendo el ranking contra el store
real, y lo que midió fue **discriminación**: que dos prompts con síntomas distintos no
devuelvan el mismo orden. Eso quedó verificado y sigue siendo cierto. Lo que nunca se
midió es la otra mitad, que es la que usa una persona: **robustez a la paráfrasis**. El
README promete que cuando abrís la sesión siguiente y *describís lo que te está pasando*,
la memoria te devuelve lo que ya se probó. Nadie describe un síntoma con las palabras
exactas con las que un modelo lo escribió la noche anterior.

**Lo que encontró, y lo que se cambió por eso.** Con el piso único en 2 tokens, el
enganche por síntoma se caía a 3 de 14 paráfrasis. Este experimento es lo que motivó la
**enmienda 0.3.6**: el piso deja de ser una constante única y pasa a ser dos, porque una
frase destilada por el modelo y un mensaje de error crudo no son la misma clase de texto.

    lo destilado (`signals`, `valid_when`, `projected_signals`)  piso 1
    lo crudo     (mensajes de error de pasos `tool_failure`)      piso 2

No es una preferencia y la medición está abajo: bajar el piso de lo **crudo** a 1 produce
un falso positivo sobre los errores reales de este store, y dejarlo en 2 no produce
ninguno — que es exactamente lo que spec §5.10 había documentado con `Exit code 1`. Bajar
el de lo **destilado** triplica el enganche por paráfrasis sin mover el control negativo.

**Esto cambió el brazo S1 del benchmark, y queda registrado.** PREREG §2 dice que la
configuración de retrieval es una constante del experimento y que dos corridas de `S1` con
distinto ranking no son comparables. El pre-registro todavía está en BORRADOR, así que el
cambio es legítimo; lo que no sería legítimo es que fuera silencioso. Está en spec §5.10
(enmienda 0.3.6), en `LATER.md`, y el número que lo justifica es el que imprime este
archivo.

**Qué NO hace este archivo:**

- **No escribe en ningún store.** Sólo compara frases contra frases.
- **No cierra ningún gate.** Los tests que defienden el cambio están en
  `tests/test_retrieve.py`; esto es la medición que lo motivó, no su gate.

**El sesgo que tiene, dicho antes de que lo encuentre otro:** las paráfrasis las escribí
yo. Están todas acá abajo, en texto plano, para que se puedan discutir de a una. Si
alguien piensa que una es tramposa —demasiado lejos, o demasiado cerca—, la edita y vuelve
a correr. Un corpus de paráfrasis escrito por quien mide es material de trabajo, no
evidencia. Lo que sí es evidencia es el **control negativo**, que no depende de mi
criterio: son prompts de otro planeta y ninguno tiene que enganchar nunca.

    python3 experimentos/05-enganche-por-parafrasis.py
    python3 experimentos/05-enganche-por-parafrasis.py --alternativas
"""

import argparse
import difflib
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from nightshift import retrieve  # noqa: E402

# ── El material ───────────────────────────────────────────────────────────────────────
# Las frases reales de la única candidata del store de este repo (`fff6af83`), consolidada
# por `claude -p` en la corrida de dream del 2026-08-27T15:25:34Z. Están copiadas acá para
# que el experimento corra en un clone limpio sin depender del store de nadie. Son las
# mismas que publica `experimentos/README.md`.
SENALES_OBSERVADAS = [
    "Todos los pasos de herramienta llegan con el resumen vacío.",
    "El desenlace de cada trayectoria es desconocido.",
    "La observacion de fin de turno acumula la misma señal desconocida.",
    "Las trayectorias sólo se distinguen por cantidad de pasos y nombre de herramienta.",
    "Todas las trayectorias caen en el tipo generico.",
    "Que el vacío sea uniforme: ninguna trayectoria, ningún paso y ningún desenlace trae "
    "contenido, lo que descarta un caso mal capturado y apunta a que la etapa de "
    "extracción nunca escribe el campo.",
]

PROYECCIONES = [
    "El retrieval devuelve coincidencias por forma estructural sin relación con el "
    "contenido del trabajo.",
    "Las memorias consolidadas de trabajos distintos resultan casi idénticas entre sí.",
    "Los contadores de cobertura reportan salud plena porque cuentan registros presentes, "
    "no registros con contenido.",
    "Una revisión manual de un registro reciente muestra la estructura completa y todos "
    "los campos de texto en blanco.",
]

# Cómo lo diría una persona que tiene el síntoma delante y nunca leyó la frase del modelo.
PARAFRASIS = [
    "ninguna de las acciones que ejecute quedo con descripcion",
    "las tool calls se registran pero sin ningun detalle de lo que hicieron",
    "no se que hizo el agente porque los registros no tienen informacion",
    "no puedo saber si la sesion termino bien o mal",
    "todas las sesiones me quedan sin resultado final",
    "las trayectorias son indistinguibles, solo cambia el numero de pasos",
    "todo me cae en la categoria por defecto, nada se clasifica",
    "el vacio es parejo en todos lados, no parece un caso aislado",
]

PARAFRASIS_PROYECTADAS = [
    "la busqueda me trae siempre lo mismo sin importar que le pregunte",
    "el ranking no cambia aunque cambie el texto que le paso",
    "dos resumenes de tareas diferentes me salieron practicamente iguales",
    "las metricas dicen que esta todo bien pero es mentira",
    "abri un registro guardado y estaba todo vacio, los campos existen pero no tienen nada adentro",
    "los datos se guardan pero cuando los leo no hay texto en ningun lado",
]

# Control negativo. Ninguno debe enganchar con nada del corpus: si enganchan, el matcher no
# reconoce síntomas, reconoce texto. Es el único lado que no depende de mi criterio.
CONTROL = [
    "el css del boton de login quedo desalineado en mobile",
    "necesito agregar un indice a la tabla de usuarios porque la query tarda 3 segundos",
    "el deploy a produccion falla con un error de certificado ssl vencido",
    "quiero renombrar la variable foo a bar en todo el proyecto",
    "como configuro el timezone del servidor",
    "agregame un endpoint nuevo que devuelva el healthcheck",
]

# Errores crudos de las trayectorias reales de este repo. Son la razón por la que el piso
# de lo crudo NO baja: acá una sola palabra en común no es señal, es andamiaje del harness.
FALLOS_CRUDOS = [
    "(eval):95: parse error near `done'",
    "Traceback (most recent call last):\n  File \"<string>\", line 4, in <module>",
    "<REPO>/cli.py:1035:  % (\"cobertura\", salud[\"with_outcome\"], salud[\"cells\"]))",
]


# ── Los matchers que se comparan ──────────────────────────────────────────────────────
# El primero es el que corre hoy sobre texto destilado. Los otros existen sólo para poner
# un número al lado: ninguno está instalado.

def destilado(tokens_prompt, frases):
    """Lo que corre hoy sobre `signals` / `valid_when` / `projected_signals`."""
    return retrieve._enganche(tokens_prompt, frases, retrieve.MIN_TOKENS_DESTILADO)


def crudo(tokens_prompt, frases):
    """Lo que corre hoy sobre los mensajes de error de pasos `tool_failure`."""
    return retrieve._enganche(tokens_prompt, frases, retrieve.MIN_TOKENS_CRUDO)


def prefijo(tokens_prompt, frases, n=5):
    """Empareja por los primeros n caracteres: 'registro'/'registros' cuentan igual.

    Es el sustituto pobre de un stemmer y no pretende ser otra cosa: compra la familia
    morfológica, no compra un solo sinónimo.
    """
    if not tokens_prompt:
        return 0
    raices = {t[:n] for t in tokens_prompt}
    mejor = 0
    for frase in frases or ():
        mejor = max(mejor, len(raices & {t[:n] for t in retrieve._tokens(frase)}))
    return mejor if mejor >= 2 else 0


def difuso(tokens_prompt, frases, corte=0.82):
    """Cada token contra cada token por `difflib`. Tolera plurales y tipeos, no sinónimos."""
    if not tokens_prompt:
        return 0
    mejor = 0
    for frase in frases or ():
        tokens_frase = retrieve._tokens(frase)
        comunes = sum(1 for a in tokens_prompt
                      if any(difflib.SequenceMatcher(None, a, b).ratio() >= corte
                             for b in tokens_frase))
        mejor = max(mejor, comunes)
    return mejor if mejor >= 2 else 0


MATCHERS = [
    ("antes: piso único 2", crudo),
    ("ahora: destilado piso 1", destilado),
    ("prefijo de 5", prefijo),
    ("difflib 0.82", difuso),
]


def _tasa(matcher, prompts, corpus):
    return sum(1 for p in prompts if matcher(retrieve._tokens(p), corpus)), len(prompts)


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--alternativas", action="store_true",
                    help="comparar contra dos matchers de stdlib que no se instalaron")
    args = ap.parse_args()

    todo = SENALES_OBSERVADAS + PROYECCIONES
    casos = PARAFRASIS + PARAFRASIS_PROYECTADAS

    print("enganche por síntoma: la frase textual contra la paráfrasis")
    print(f"corpus: {len(SENALES_OBSERVADAS)} señales observadas + "
          f"{len(PROYECCIONES)} proyectadas, de la candidata fff6af83")
    print(f"pisos vigentes: destilado={retrieve.MIN_TOKENS_DESTILADO} "
          f"crudo={retrieve.MIN_TOKENS_CRUDO}")
    print()

    print("1. Control positivo — la frase textual tiene que enganchar siempre")
    a, n = _tasa(destilado, SENALES_OBSERVADAS, SENALES_OBSERVADAS)
    b, m = _tasa(destilado, PROYECCIONES, PROYECCIONES)
    print(f"   señales observadas   {a}/{n}")
    print(f"   proyecciones         {b}/{m}")
    print()

    print("2. La paráfrasis — lo que realmente escribe una persona")
    for etiqueta, prompts, corpus in (
            ("señales observadas", PARAFRASIS, SENALES_OBSERVADAS),
            ("proyecciones", PARAFRASIS_PROYECTADAS, PROYECCIONES)):
        antes, _ = _tasa(crudo, prompts, corpus)
        ahora, total = _tasa(destilado, prompts, corpus)
        print(f"   {etiqueta:20s} antes {antes}/{total}   ahora {ahora}/{total}")
        for p in prompts:
            viejo = "sí" if crudo(retrieve._tokens(p), corpus) else "no"
            nuevo = "sí" if destilado(retrieve._tokens(p), corpus) else "NO"
            marca = "  " if viejo == nuevo.lower() else " ←"
            print(f"      {viejo} → {nuevo}{marca} {p}")
    print()

    print("3. Control negativo — tiene que dar 0, o el matcher no reconoce síntomas")
    fp, tot = _tasa(destilado, CONTROL, todo)
    print(f"   sobre lo destilado   {fp}/{tot}")
    print()

    print("4. Por qué el piso de lo CRUDO no baja")
    print("   Los mismos prompts de control, contra los errores reales de este store:")
    for piso, etiqueta in ((1, "piso 1"), (retrieve.MIN_TOKENS_CRUDO, "piso 2 (vigente)")):
        falsos = sum(1 for p in CONTROL
                     if retrieve._enganche(retrieve._tokens(p), FALLOS_CRUDOS, piso))
        print(f"      {etiqueta:18s} falsos positivos {falsos}/{len(CONTROL)}")
    print("   Es el caso que spec §5.10 ya había documentado con `Exit code 1`.")
    print()

    if args.alternativas:
        print("5. Lo que se comparó y no se instaló")
        print("   Acá cada prompt se mide contra el corpus ENTERO —observadas y")
        print("   proyectadas juntas—, que es la condición real del retrieval: una")
        print("   trayectoria engancha por cualquiera de sus frases. Por eso el total")
        print("   no es la suma del desglose de arriba, que las separa a propósito.")
        print()
        print(f"   {'matcher':26s} {'paráfrasis':>12s} {'falsos':>9s}")
        print(f"   {'-' * 26} {'-' * 12} {'-' * 9}")
        for nombre, fn in MATCHERS:
            ok, _ = _tasa(fn, casos, todo)
            falsos, _ = _tasa(fn, CONTROL, todo)
            print(f"   {nombre:26s} {ok:>7d}/{len(casos):<4d} {falsos:>4d}/{len(CONTROL):<4d}")
        print()
        print("   Un matcher sólo sirve si sube la columna de paráfrasis SIN subir la de")
        print("   falsos. `prefijo` y `difflib` no compran nada acá: el problema no es")
        print("   morfológico —plurales, tipeos— sino de sinónimo, y ninguno de los dos")
        print("   sabe que 'descripcion' y 'resumen' son la misma cosa. Eso necesitaría")
        print("   embeddings, que chocan con ADR-003 (stdlib, sin red). Queda en LATER.md.")
    print()
    print("No cierra ningún gate. El gate del cambio son los tests de test_retrieve.py.")


if __name__ == "__main__":
    main()
