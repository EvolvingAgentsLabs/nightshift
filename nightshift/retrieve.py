"""Retrieval estructural e inyección en SessionStart (M2).

Sin dream todavía: se inyectan trayectorias crudas recientes del mismo tipo de tarea
(plan §3, M2). El ranking es determinista y cada inyección queda registrada con su
trayectoria origen, para que `/nightshift:why` pueda reconstruirla — que es el gate
de M2 y la condición de éxito 3 de la spec.
"""

from __future__ import annotations

import json
import math
import re
import shlex
import subprocess
import unicodedata
from datetime import datetime, timedelta, timezone

from . import context, store

# Pesos del ranking. Determinista y auditable: `why` los reimprime tal cual.
W_SAME_TASK = 2.0
W_SAME_REPO = 1.0
W_DECISIVE = 1.0
W_TESTS_PASSED = 1.5
W_USER_CORRECTED = -1.0
W_DAY_DECAY = -0.05
# Enganche por síntoma (ADR-004). El prompt describe lo que se está viendo; una señal
# describe lo que se vio antes. Cuando coinciden, esta trayectoria habla del problema
# que hay delante y no sólo del mismo tipo de tarea.
#
# Lo **proyectado** pesa la mitad de lo observado, y no es una calibración: una señal
# observada está en los pasos, una proyectada la anticipó un modelo desde un dibujo y no
# la vio nadie. Pesarlas igual sería subir una conjetura a la categoría de evidencia.
W_SIGNAL_MATCH = 1.5
W_PROJECTED_MATCH = 0.75
# Enganche por el fallo observado de una trayectoria **cruda**. Vale lo mismo que el
# enganche por señal abstraída y no es una calibración: las dos son observaciones, y la
# diferencia de confianza entre una trayectoria cruda y una consolidada ya la cobra
# `injection_weight` (0.3 contra 0.6), que es donde el proyecto guarda cuánto se cree
# una fila. Antes de esto, una trayectoria sin abstracción no tenía **ningún** enganche
# por síntoma: se rankeaba por repo, tipo de tarea y recencia, así que dos prompts que
# describen síntomas distintos daban el mismo orden — medido sobre el store real. Un
# fallo que ocurrió de verdad pesaba cero mientras una conjetura proyectada por el
# modelo pesaba 0.75. Eso invertía la jerarquía de evidencia del proyecto.
W_FAILURE_MATCH = 1.5
# Enganche por **precondición**. Es la otra clave de recuperación, y no dice lo mismo que
# las otras dos: una señal dice "esto ya lo vi", una precondición dice "esto aplica acá".
# Sin ella, una alternativa descartada cuya condición describe exactamente la situación
# que el usuario tiene delante no puntúa por eso ni un punto — y esa condición es la mitad
# del valor de conservar lo descartado (spec §4.2).
#
# Pesa menos que una señal observada y más que un síntoma proyectado, y el orden no es
# arbitrario: `signals` sale de lo que está en los pasos, `valid_when` lo **infiere** el
# modelo desde esos pasos, y `projected_signals` es lo que nadie vio. Observado > inferido
# > conjeturado. El número exacto no lo calibró nadie: lo juzga M4.
W_PRECONDITION_MATCH = 1.0

# Enmienda 0.3.10 (decidida por Matías): el logograma (ADR-007) dejó de ser sólo display
# y pasó a ser superficie de búsqueda, con **prioridad sobre los demás enganches** en el
# orden. Es la compresión más densa que la consolidación produce —dos a cuatro palabras
# que nombran el mecanismo— y su piso es duro: con textos de ese largo, exigir 2
# coincidencias es exigir casi el signo entero, que es lo que evita que una palabra suelta
# lo dispare. Pesa igual que una señal: la prioridad es una regla de orden, no un peso,
# igual que en la 0.3.7.
W_LOGOGRAM_MATCH = 1.5
MIN_TOKENS_LOGOGRAMA = 2

# El fallback semántico (enmienda de ADR-003, 2026-08-29, decidida por Matías) pesa lo
# mismo que una conjetura: una similitud inferida por un modelo de embeddings no es una
# palabra que el usuario escribió, y la jerarquía observado > inferido > conjeturado
# también ordena los enganches. Sólo corre cuando la pasada léxica no encontró nada en
# esa fila y hay `embedding_command` configurado.
W_SEMANTIC_MATCH = 0.75

# Cuántas palabras de contenido tienen que coincidir para llamarlo enganche.
#
# **Son dos pisos y no uno, y la diferencia se midió** (enmienda 0.3.6; el experimento es
# `experimentos/05-enganche-por-parafrasis.py`). Un piso único trataba igual a dos clases
# de texto que no se parecen en nada:
#
# - Una frase de `abstraction` la escribió el modelo destilando: es una oración curada,
#   sin relleno, donde una sola palabra de contenido compartida ya es señal.
# - Un mensaje de error crudo es mayormente andamiaje del harness. Ahí una sola palabra
#   no dice nada, y es el caso que spec §5.10 documentó: "exit" y "code" alcanzaban para
#   hermanar un `parse error` con un error de formateo.
#
# Lo que costaba el piso único: el enganche por síntoma **se caía a cero con la
# paráfrasis**, que es exactamente como lo escribe una persona. Medido sobre las frases
# reales de la candidata `fff6af83`, con piso 2 enganchaban 3 de 14 paráfrasis; con piso 1
# sobre lo destilado, 9 de 14 — y el control negativo se queda en 0 de 6 en los dos casos.
# Sobre los fallos crudos del mismo store, en cambio, bajar el piso a 1 produce un falso
# positivo y el piso 2 ninguno: por eso el piso de abajo no se toca.
#
# La spec ya afirmaba esta jerarquía en prosa —"con abstracción manda la abstracción: es
# lo destilado; el enganche por fallo es el piso"— y el código la contradecía cobrándoles
# el mismo peaje a las dos.
# **Enmienda 0.3.10 (2026-08-28, decidida por Matías):** el piso de lo destilado sube a
# 2. La 0.3.6 lo había fijado en 1 midiendo contra un store de UNA candidata; con el store
# crecido, `experimentos/13` midió que con piso 1 sólo 4 de 17 prompts verdaderos entran
# al top-3 y 17 de 24 ajenos enganchan algo, y con piso 2 mejoran las dos mitades (5 de 17
# y 2 de 24). El `15` lo reprodujo sobre material diseñado: 4 de 6 paráfrasis cruzaban con
# casos ajenos. Subir el piso era mejor en las dos mitades, no un intercambio.
MIN_TOKENS_DESTILADO = 2
MIN_TOKENS_CRUDO = 2

# Los cuatro motivos que dicen *esta fila habla del problema que el usuario tiene
# delante*. Los otros —`same_repo`, `same_task_type`, `has_decisive_step`,
# `tests_passed`— dicen algo sobre la fila, no sobre el prompt.
#
# **Un enganche ordena antes que cualquier puntaje sin enganche** (enmienda 0.3.7), y eso
# es una regla de orden, no un peso: no se inventa ningún número.
#
# El motivo se midió sobre el store real. Con un prompt que engancha por síntoma
# proyectado, la única fila que hablaba del problema quedaba **tercera de tres**:
#
#     1.045  closed     same_repo,has_decisive_step,tests_passed
#     1.030  closed     same_repo,has_decisive_step,tests_passed
#     1.009  candidate  same_repo,projected_match      <- la única que engancha
#
# `has_decisive_step` + `tests_passed` suman 2,5 puntos que no dependen del prompt: una
# trayectoria que salió bien y corrió tests le gana a una que anticipó exactamente este
# síntoma. Con `max_injected` en 3 entraba por poco; con una cuarta trayectoria en verde
# en el store, la proyección se cae de la inyección — y una proyección que no llega antes
# del error no proyectó nada.
MOTIVOS_DE_ENGANCHE = frozenset(
    ("signal_match", "projected_match", "precondition_match", "failure_match",
     "logogram_match", "semantic_match"))

# Cuántos fallos de una trayectoria se miran. Una trayectoria de 400 pasos tiene un
# puñado de fallos, no cuatrocientos, y el ranking corre dentro de un hook: el tope es
# para que el costo no dependa del largo de la sesión que se capturó.
MAX_FALLOS_CONSULTADOS = 20

# La ideación se pidió de tres a seis oraciones y el modelo devuelve, medido, cerca de
# 1800 caracteres. Inyectarla entera gasta más contexto que las tres trayectorias juntas,
# y el que la necesita completa tiene `why`. Se corta en la última oración que entra: un
# dibujo cortado a la mitad de una frase es peor que uno más corto.
MAX_IDEACION_CHARS = 420

_PALABRA_RE = re.compile(r"[a-z0-9_]{4,}")
# El encabezado que el harness le pone a un comando que salió distinto de cero. Es
# andamiaje, no síntoma: aparece en **todos** los fallos, así que dos palabras en común
# —"exit" y "code"— alcanzaban para hermanar dos trayectorias que no comparten nada.
# Medido sobre el store real: sin sacarlo, un prompt que dijera "exit code" enganchaba
# con un `parse error near done` y con un error de formateo de cobertura por igual.
# Se saca sólo para rankear; lo que está guardado no se toca.
_ENCABEZADO_DE_FALLO_RE = re.compile(r"^\s*exit code\s+-?\d+\s*", re.I)
# Palabras que aparecen en casi cualquier prompt de trabajo: coincidir en ellas no dice
# nada. La lista es corta a propósito — filtrar de más es empezar a decidir qué se
# parece a qué, y eso es justo lo que el ranking tiene que hacer de forma auditable.
_VACIAS = frozenset("""
para pero como cuando donde porque esto esta este estos estas tiene hacer hace desde
sobre entre todo toda todos todas algo alguna alguno mismo misma solo sólo tambien
también aunque entonces despues después antes ahora bien mejor peor mucho poco
that this with from have there their which when where what
""".split())

# Los marcadores que deja el redactor. No son contenido: son la huella de lo que se
# borró, y aparecen en casi cualquier fallo capturado (`Exit code 1 <REPO><PATH>`).
# Contarlos como coincidencia hermanaría dos trayectorias por lo que **no** se guardó.
# El test `test_redaccion.py` no existe para esto: hay un test acá que corre el redactor
# de verdad y falla si aparece un marcador nuevo que esta lista no conozca.
_MARCADORES_DE_REDACCION = frozenset(
    "repo path secret credentials email blob truncated".split())
_VACIAS = _VACIAS | _MARCADORES_DE_REDACCION

# Palabras que dicen **que** algo se rompió, no **qué** se rompió. No son vacías —suman
# perfectamente bien como segunda coincidencia, donde la otra palabra dice de qué se
# habla— pero no pueden sostener un enganche ellas solas: "falla" es verdad en cualquier
# prompt de debugging, y con el piso de lo destilado en 1 alcanzaba para hermanar un
# certificado SSL vencido con una etapa que no valida contenido.
#
# Medido, no estimado (enmienda 0.3.6, `experimentos/05-enganche-por-parafrasis.py`).
# Sobre las frases reales de la candidata `fff6af83` contra un control de nueve prompts
# ajenos, los enganches de una sola palabra se reparten así:
#
#     verdaderos positivos, los carga un sustantivo del dominio:
#         vacio · texto · registro · paso · ninguna · ningun
#     falsos positivos, los carga un predicado:
#         falla
#
# La lista es corta por la misma razón que `_VACIAS`: filtrar de más es empezar a decidir
# qué se parece a qué, y eso es justo lo que el ranking tiene que hacer de forma
# auditable. Es la misma clase de exclusión que `_ENCABEZADO_DE_FALLO_RE` — "exit code"
# tampoco es un síntoma.
_PREDICADOS_DE_FALLO = frozenset("""
falla fallo fallan fallando fallar error errores problema problemas bug bugs
rompe rompio roto rompen anda andaba funciona funcionaba
""".split())


def _canonica(palabra):
    """El plural del castellano, plegado a una forma canónica. Determinista.

    Enmienda 0.3.11. No es un stemmer: son las dos letras del plural regular y nada más.
    Lo que ya se probó y NO compra nada es el prefijo y `difflib` (LATER.md, "el enganche
    no sabe de sinónimos") — eso era sinónimo. Esto es morfología: `clave` y `claves` son
    la misma palabra, y con el piso en 2 esa diferencia costaba el enganche entero.

    La forma canónica **no tiene que ser una palabra real**: tiene que ser LA MISMA para
    el singular y el plural. `clave→clav ← claves` y `error→error ← errores` no salen con
    una sola regla de recorte, pero sí con dos aplicadas a los dos lados: sacar la `s`
    final, y después la `e` final. Los dos textos se pliegan igual, y eso es lo único que
    la coincidencia necesita.
    """
    if len(palabra) >= 5 and palabra.endswith("s"):
        palabra = palabra[:-1]
    if len(palabra) >= 5 and palabra.endswith("e"):
        palabra = palabra[:-1]
    return palabra


def _tokens(texto):
    """Palabras de contenido, normalizadas. Determinista y sin dependencias.

    Se sacan los acentos porque "análisis" y "analisis" son la misma palabra para esto, y
    una coincidencia que depende de cómo alguien escribió una tilde no es estructural. El
    plural se pliega por el mismo motivo (0.3.11): "clave" y "claves" difieren en cómo se
    contó, no en de qué se habla. Se pliega a **una** forma canónica y no se agregan las
    dos: con las dos en el conjunto, una sola palabra en plural contaría como dos
    coincidencias y bajaría el piso de facto a 1.
    """
    if not texto:
        return frozenset()
    plano = unicodedata.normalize("NFKD", texto.lower())
    plano = "".join(c for c in plano if not unicodedata.combining(c))
    return frozenset(_canonica(t) for t in _PALABRA_RE.findall(plano)
                     if t not in _VACIAS)


# La lista cruda, plegada con la misma regla que los tokens contra los que se compara.
_PREDICADOS_CANONICOS = frozenset(_canonica(w) for w in _PREDICADOS_DE_FALLO)


def _enganche(tokens_prompt, frases, piso=MIN_TOKENS_CRUDO):
    """¿Alguna de estas frases habla de lo mismo que el prompt?

    Devuelve la cantidad de palabras de contenido en común de la frase que más comparte.
    Cero es "no engancha".

    `piso` es explícito en cada llamada a propósito: es la decisión de si el texto que se
    compara es destilado o crudo, y esa decisión pertenece a quien sabe qué está pasando,
    no a un default. El default es el conservador.
    """
    if not tokens_prompt:
        return 0
    mejor = 0
    for frase in frases or ():
        comunes = tokens_prompt & _tokens(frase)
        # Un enganche que se apoya sólo en predicados de fallo no dice de qué se habla:
        # "algo falla" es cierto en cualquier prompt de debugging. Tiene que quedar al
        # menos una palabra que nombre la cosa. Contra la forma canónica (0.3.11): los
        # tokens ya vienen plegados, y un `rompe` plegado que escapara de la lista cruda
        # volvería a sostener enganches él solo.
        if not (comunes - _PREDICADOS_CANONICOS):
            continue
        if len(comunes) > mejor:
            mejor = len(comunes)
    return mejor if mejor >= piso else 0


def _engancha(reasons: str) -> bool:
    """¿Alguno de los motivos de esta fila la ata al prompt?

    Se lee de la cadena de motivos y no de una cuarta posición en la tupla a propósito:
    `(score, reasons, row)` es lo que consumen `render`, el hook y `why`, y estirarla
    obligaría a tocar los tres para una decisión que ya está escrita en los motivos.
    """
    return bool(MOTIVOS_DE_ENGANCHE & set((reasons or "").split(",")))


def _fallos_observados(conn, trajectory_id):
    """Los mensajes de error de los pasos que fallaron de verdad.

    **Sólo `tool_failure`**, y el motivo es una medición, no una preferencia: la
    heurística de `decisive` marca también cada comando de test que corre, y sobre el
    store real eso es el 38% de los pasos. Enganchar contra el texto de un test en verde
    —"Ran 255 tests ... OK"— haría que cualquier prompt que hable de tests coincida con
    todo, que es exactamente el fallo que ya costó una vez (HANDOFF §4: la heurística de
    señal decisiva marcaba el 41% de los pasos porque buscaba el comando como subcadena).

    Un fallo, en cambio, es una observación: lo que se vio cuando el problema se
    manifestó. Es la clave de recuperación que corresponde a "el mismo bug con otra
    cara" mientras no haya abstracción — y si la hay, manda la abstracción.
    """
    filas = conn.execute(
        "SELECT error_message FROM steps WHERE trajectory_id = ? AND kind = 'tool_failure'"
        " AND error_message IS NOT NULL AND error_message != ''"
        " ORDER BY idx DESC LIMIT ?",
        (trajectory_id, MAX_FALLOS_CONSULTADOS)).fetchall()
    return [_ENCABEZADO_DE_FALLO_RE.sub("", f["error_message"]) for f in filas]


def _age_days(created_at: str) -> float:
    try:
        then = datetime.strptime(created_at, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc)
    except ValueError:
        return 999.0
    return max(0.0, (datetime.now(timezone.utc) - then).total_seconds() / 86400.0)


# --------------------------------------------- el fallback semántico (ADR-003, enmienda)
#
# El problema que resuelve está en LATER.md desde la enmienda 0.3.6: `resumen` y `memoria
# consolidada` no comparten ni una palabra, y ninguna regla barata los pliega. La decisión
# de Matías del 2026-08-29 mete embeddings — y la restricción que ordena el diseño es la
# de siempre (ADR-006): **el embedding es un comando, no un servicio.** nightshift no
# habla con la red nunca; el comando del usuario hace lo que el usuario quiera, con su
# riesgo. `tools/embed-ollama.sh` envuelve al ollama local.
#
# Contrato del comando: lee `{"texts": [...]}` por stdin, escribe `{"vectors": [...]}`
# por stdout. Cualquier fallo —comando ausente, timeout, salida malformada— apaga la
# pasada en silencio: esto corre dentro de un hook, y un hook roto tiene que ser
# indistinguible de un hook apagado (spec §7.2).

def _vectores(cfg, textos):
    """Los embeddings de estos textos, por el comando del usuario. None si no se pudo."""
    comando = cfg.get("embedding_command")
    if not comando or not textos:
        return None
    if isinstance(comando, str):
        comando = shlex.split(comando)
    try:
        out = subprocess.run(comando, input=json.dumps({"texts": textos}),
                             capture_output=True, text=True,
                             timeout=cfg.get("embedding_timeout_seconds", 20))
        if out.returncode != 0:
            return None
        vectores = json.loads(out.stdout).get("vectors")
    except (OSError, ValueError, subprocess.TimeoutExpired):
        return None
    if not isinstance(vectores, list) or len(vectores) != len(textos):
        return None
    return vectores


def _coseno(a, b):
    dot = sum(x * y for x, y in zip(a, b))
    na = math.sqrt(sum(x * x for x in a))
    nb = math.sqrt(sum(y * y for y in b))
    return dot / (na * nb) if na and nb else 0.0


def _superficies_de(conn, row):
    """Los mismos textos contra los que engancha la pasada léxica. Ni uno más.

    Darle al fallback una superficie que las palabras no miran —`pattern`, los pasos—
    sería cambiar el tratamiento por la puerta de atrás: el semántico relaja el CÓMO se
    compara, nunca el QUÉ.
    """
    textos = []
    if row["abstraction_json"]:
        abstraccion = json.loads(row["abstraction_json"])
        textos.extend(abstraccion.get("signals") or [])
        if abstraccion.get("decisive_signal"):
            textos.append(abstraccion["decisive_signal"])
        textos.extend(c.get("condition", "") for c in
                      json.loads(row["valid_when_json"] or "[]")
                      if isinstance(c, dict))
        abiertas, confirmadas, _ = _proyectadas(conn, row)
        textos.extend(abiertas + confirmadas)
    if "logogram" in row.keys() and row["logogram"]:
        textos.append(row["logogram"])
    return [t for t in textos if t]


def _pasada_semantica(conn, prompt, items, cfg):
    """Marca `semantic_match` en las filas que el coseno alcanza. Muta `items` in place.

    Una sola llamada al comando por retrieval: el prompt más todas las superficies de
    todas las filas sin enganche, en tanda. El peso es el de una conjetura
    (`W_PROJECTED_MATCH`): una similitud inferida por un modelo no es una palabra que el
    usuario escribió, y la jerarquía observado > inferido > conjeturado también ordena
    los enganches.
    """
    piso = float(cfg.get("semantic_threshold", 0.40))
    superficies_por_item = [_superficies_de(conn, item[2]) for item in items]
    textos = [prompt]
    for superficies in superficies_por_item:
        textos.extend(superficies)
    vectores = _vectores(cfg, textos)
    if vectores is None:
        return
    v_prompt, resto = vectores[0], vectores[1:]
    i = 0
    for item, superficies in zip(items, superficies_por_item):
        mejor = 0.0
        for _ in superficies:
            mejor = max(mejor, _coseno(v_prompt, resto[i]))
            i += 1
        if mejor >= piso:
            item[0] += W_SEMANTIC_MATCH * float(item[2]["injection_weight"] or 0.3)
            item[1].append("semantic_match")


def candidates(conn, *, task_type, repo_fingerprint, cfg, exclude_id=None, prompt=None):
    lookback = cfg.get("retrieval_lookback_days", 30)
    cutoff = (datetime.now(timezone.utc) - timedelta(days=lookback)).strftime("%Y-%m-%dT%H:%M:%SZ")
    rows = conn.execute(
        "SELECT * FROM trajectories WHERE status IN ('closed','candidate','procedure')"
        " AND created_at >= ? ORDER BY created_at DESC, rowid DESC LIMIT 200",
        (cutoff,)).fetchall()

    # El texto del prompt **no se persiste** (spec §5.6): se tokeniza acá, en memoria,
    # y lo único que queda registrado es la etiqueta del motivo — `signal_match`,
    # `projected_match` — nunca las palabras que engancharon.
    tokens_prompt = _tokens(prompt)

    scored = []
    for row in rows:
        if exclude_id and row["id"] == exclude_id:
            continue
        same_repo = row["repo_fingerprint"] == repo_fingerprint
        if not same_repo and not cfg.get("cross_repo", False):
            continue
        if not same_repo and not row["abstraction_json"]:
            # Cross-repo sin abstracción es transferir detalle de repo, no patrón.
            continue

        reasons = []
        score = 0.0
        # `general` no es un tipo de tarea: es "todavía sin clasificar". Contarlo como
        # coincidencia hacía que `SessionStart` — que corre antes de que el usuario
        # escriba — reportara `same_task_type` emparejando dos trayectorias sin
        # clasificar. Parecía retrieval estructural y no lo era (spec §5.7).
        classified = task_type != context.DEFAULT_TASK_TYPE
        if classified and row["task_type"] == task_type:
            score += W_SAME_TASK
            reasons.append("same_task_type")
        if same_repo:
            score += W_SAME_REPO
            reasons.append("same_repo")
        decisive = conn.execute(
            "SELECT COUNT(*) c FROM steps WHERE trajectory_id = ? AND decisive = 1",
            (row["id"],)).fetchone()["c"]
        if decisive:
            score += W_DECISIVE
            reasons.append("has_decisive_step")
        if row["outcome_result"] == "tests_passed":
            score += W_TESTS_PASSED
            reasons.append("tests_passed")
        elif row["outcome_result"] == "user_corrected":
            score += W_USER_CORRECTED
            reasons.append("user_corrected")
        # Enganche por síntoma. Sólo hay prompt en `UserPromptSubmit`: en
        # `SessionStart` esto no aporta nada y no se cobra, que es lo correcto —
        # inventar un enganche sin texto sería el mismo error que contar `general`
        # como coincidencia de tipo de tarea.
        if tokens_prompt and not row["abstraction_json"]:
            # Sin abstracción, la única señal observada que tiene esta trayectoria son
            # sus fallos. Es el caso mayoritario de un store real: dream produce cero
            # candidatas sobre sesiones de desarrollo largas (LATER.md, "un día no es una
            # trayectoria"), así que casi todo lo que se inyecta es crudo.
            if _enganche(tokens_prompt, _fallos_observados(conn, row["id"])):
                score += W_FAILURE_MATCH
                reasons.append("failure_match")
        if tokens_prompt and row["abstraction_json"]:
            abstraccion = json.loads(row["abstraction_json"])
            senales = list(abstraccion.get("signals") or [])
            if abstraccion.get("decisive_signal"):
                senales.append(abstraccion["decisive_signal"])
            # Las tres son texto destilado por el modelo, no crudo: van con el piso de
            # abajo. Es lo que hace que el enganche sobreviva a que el usuario describa
            # el síntoma con sus palabras y no con las del modelo.
            if _enganche(tokens_prompt, senales, MIN_TOKENS_DESTILADO):
                score += W_SIGNAL_MATCH
                reasons.append("signal_match")
            condiciones = [c.get("condition", "") for c in
                           json.loads(row["valid_when_json"] or "[]")
                           if isinstance(c, dict)]
            if _enganche(tokens_prompt, condiciones, MIN_TOKENS_DESTILADO):
                score += W_PRECONDITION_MATCH
                reasons.append("precondition_match")
            # Las refutadas no están acá: enganchar por una conjetura que alguien ya
            # descartó es traer al agente al problema equivocado con evidencia negativa.
            abiertas, confirmadas, _ = _proyectadas(conn, row)
            if _enganche(tokens_prompt, abiertas + confirmadas, MIN_TOKENS_DESTILADO):
                score += W_PROJECTED_MATCH
                reasons.append("projected_match")
        # El logograma (ADR-007, enmienda 0.3.10). Vive en su columna y no en el JSON: se
        # chequea aparte, y su piso exige casi el signo entero.
        if tokens_prompt and "logogram" in row.keys() and row["logogram"]:
            if _enganche(tokens_prompt, [row["logogram"]], MIN_TOKENS_LOGOGRAMA):
                score += W_LOGOGRAM_MATCH
                reasons.append("logogram_match")
        score += W_DAY_DECAY * _age_days(row["created_at"])
        score *= float(row["injection_weight"] or 0.3)

        if score <= 0:
            continue
        scored.append([score, reasons, row])

    # Fallback semántico (enmienda de ADR-003, 2026-08-29). Sólo para las filas que las
    # palabras NO alcanzaron, y sólo si el usuario enchufó un `embedding_command`: sin
    # comando, esto no corre y el ranking es letra por letra el de antes. Es la respuesta
    # al problema de los sinónimos de LATER.md — `resumen`/`memoria consolidada` no se
    # pliegan con ninguna regla barata — y su alcance está medido en la calibración de
    # `config.py`: sinónimos de registro parecido sí; síntoma contra mecanismo abstracto,
    # no.
    if prompt and cfg.get("embedding_command"):
        sin_enganche = [item for item in scored
                        if not (MOTIVOS_DE_ENGANCHE & set(item[1]))]
        if sin_enganche:
            _pasada_semantica(conn, prompt, sin_enganche, cfg)

    empaquetadas = [(score, ",".join(reasons) or "recent", row)
                    for score, reasons, row in scored]
    # Primero las que enganchan por logograma (enmienda 0.3.10: es el signo entero, la
    # coincidencia más específica que la consolidación produce), después cualquier otro
    # enganche, después el puntaje. Sin prompt no engancha nada y el orden es exactamente
    # el de antes: `SessionStart` corre antes de que el usuario escriba, y ahí nada de
    # esto cambia una sola fila.
    empaquetadas.sort(key=lambda item: (
        0 if "logogram_match" in (item[1] or "").split(",")
        else (1 if _engancha(item[1]) else 2),
        -item[0], item[2]["created_at"]))
    return empaquetadas


def _recortar(texto, limite=MAX_IDEACION_CHARS):
    """Corta en la última oración que entra. Nunca a la mitad de una frase."""
    texto = texto.strip()
    if len(texto) <= limite:
        return texto
    corte = texto[:limite]
    punto = corte.rfind(". ")
    if punto > limite // 3:
        return corte[:punto + 1] + " […] `why` lo muestra entero."
    return corte.rsplit(" ", 1)[0] + "… […] `why` lo muestra entero."


def _proyectadas(conn, row):
    """Conjeturas vivas de esta fila: `(abiertas, confirmadas, cuántas refutadas)`.

    **Una refutada no vuelve.** Alguien fue a mirar y sabe por qué no puede pasar; seguir
    ofreciéndola como síntoma a anticipar es peor que no haberla proyectado nunca. Se
    cuenta, para que la inyección pueda decir que hubo trabajo ahí, y no se muestra.

    **Una confirmada no asciende.** Sigue pesando la mitad y sigue apareciendo aparte de
    `signals`: confirmarla dice que el mecanismo acertó, no que este trabajo la haya
    observado. Esa frontera es lo que ADR-004 defiende, y borrarla acá la borraría entera.

    Si la tabla todavía no tiene nada de esta fila —un store que no corrió `sync`— se cae
    al JSON, que es el dato original y nunca se toca.
    """
    filas = store.projections_of(conn, row["id"]) if conn is not None else []
    if filas:
        abiertas = [f["text"] for f in filas if f["status"] == "open"]
        confirmadas = [f["text"] for f in filas if f["status"] == "confirmed"]
        refutadas = sum(1 for f in filas if f["status"] == "refuted")
        return abiertas, confirmadas, refutadas
    if "projected_signals_json" not in row.keys() or not row["projected_signals_json"]:
        return [], [], 0
    try:
        datos = json.loads(row["projected_signals_json"])
    except (TypeError, ValueError):
        return [], [], 0
    if not isinstance(datos, list):
        return [], [], 0
    return [x for x in datos if isinstance(x, str)], [], 0


def render(conn, scored, *, max_injected, native_memory, task_type=None,
           repo_fingerprint=None):
    """Texto que se inyecta como additionalContext. Vacío si no hay nada que decir.

    `task_type` sólo cambia cómo se presenta el material: decir "del mismo tipo de
    tarea" cuando el tipo todavía es `general` sería describir un ranking que no ocurrió.

    `repo_fingerprint` decide **cuánto** se muestra de cada trayectoria. De otro repo sale
    la abstracción y nada más: los pasos traen nombres de archivo, comandos y mensajes de
    error de ese repo, y "la abstracción es lo único que puede cruzar de repo A a repo B"
    (spec §4.2) es una regla sobre lo que se emite, no sólo sobre lo que se elige.
    """
    chosen = scored[:max_injected]
    if not chosen:
        return "", []

    classified = task_type and task_type != context.DEFAULT_TASK_TYPE
    if classified:
        origen = ["Trayectorias previas del mismo tipo de tarea (`%s`)." % task_type]
    else:
        origen = [
            "Trayectorias recientes de este repo. Todavía no hay tipo de tarea:",
            "`SessionStart` corre antes de que escribas, así que esto se rankeó por repo y",
            "recencia, no por estructura.",
        ]

    lines = [
        "## nightshift — memoria procedimental (M2, trayectorias crudas)",
        "",
    ] + origen + [
        "**Ninguna está verificada**: dream fase 2 (`verify`) todavía no existe, así que",
        "esto es evidencia débil — tratalas como pistas, no como hechos. Contradecirlas",
        "con lo que veas en el repo es lo correcto, no un error.",
        "",
    ]
    # Si alguna enganchó con lo que el usuario escribió, el orden dejó de ser sólo por
    # puntaje y el texto tiene que decirlo. Un orden que el lector no puede explicar es
    # indistinguible de uno arbitrario, y `why` lo reimprime igual.
    if any(_engancha(reasons) for _, reasons, _ in chosen):
        lines += [
            "Las primeras **enganchan con lo que acabás de escribir** (`signal_match`,",
            "`projected_match`, `precondition_match`, `failure_match`): hablan del",
            "problema que tenés delante, no sólo del mismo repo o tipo de tarea. Por eso",
            "van arriba aunque su puntaje sea menor.",
            "",
        ]
    if native_memory:
        lines.append("Auto Memory tiene notas para este proyecto: son la fuente declarativa. "
                     "Lo de abajo es el proceso, no los hechos.")
        lines.append("")

    for rank, (score, reasons, row) in enumerate(chosen, start=1):
        short = row["id"][:8]
        etiqueta = {"candidate": "consolidada por dream, SIN VERIFICAR",
                    "procedure": "verificada"}.get(row["status"], "trayectoria cruda")
        otro_repo = bool(repo_fingerprint) and row["repo_fingerprint"] != repo_fingerprint
        if otro_repo:
            etiqueta += ", de otro repo"
        # Lo importado se anuncia en el encabezado y no en una nota al pie: **no se
        # observó en esta máquina**, el redactor de otro decidió qué tapaba, y ninguno de
        # sus pasos lo vio nadie de este lado. Es la misma frontera que separa `signals`
        # de `projected_signals`, y se defiende igual: diciéndola cada vez.
        if "origin" in row.keys() and row["origin"] == store.ORIGIN_EXTERNAL:
            etiqueta += ", **IMPORTADA — no se observó en esta máquina**"
        lines.append("### %d. `%s` — %s · %s (score %.2f · %s)"
                     % (rank, short, row["task_type"], etiqueta, score, reasons))
        # Una `candidate` trae el patrón abstraído; una cruda, sólo sus pasos. El agente
        # tiene que poder distinguir "esto se probó" de "esto pareció funcionar una vez"
        # (spec §6.3), y para eso el texto tiene que decir cuál es cuál.
        if row["status"] in ("candidate", "procedure") and row["abstraction_json"]:
            abstraction = json.loads(row["abstraction_json"])
            if abstraction.get("pattern"):
                lines.append("- patrón: %s" % abstraction["pattern"])
            if abstraction.get("decisive_signal"):
                lines.append("- señal decisiva del patrón: %s" % abstraction["decisive_signal"])
            for item in json.loads(row["valid_when_json"] or "[]")[:3]:
                lines.append("- aplica cuando: %s" % item.get("condition", ""))
            # El boceto del mecanismo, si dream ideó. Va antes de lo proyectado porque
            # es de donde salió: sin el dibujo, una proyección es una afirmación suelta.
            # El diagrama va entero: es dibujo y texto a la vez, y recortarlo por la
            # mitad no da un diagrama más chico, da uno roto. El tope de nodos está en
            # el prompt, que es donde se puede pedir brevedad sin romper sintaxis.
            if "diagram" in row.keys() and row["diagram"]:
                lines.append("- el mecanismo, dibujado:")
                lines.append("")
                lines.append("```mermaid")
                lines.append(row["diagram"])
                lines.append("```")
                lines.append("")
            # El otro medio de idear (ADR-007): la escena física y el signo que la nombra.
            # Van enteros y en este orden —primero el nombre, después la imagen— porque el
            # logograma es lo que se retiene de un vistazo y la escena, lo que se recorre
            # cuando el nombre resultó pertinente.
            #
            # Se **muestran**, y no entran en la superficie de búsqueda. Es una decisión y
            # está medida: contra una compresión de dos a cuatro palabras el enganche por
            # palabras funciona peor que contra un síntoma, no mejor, y agregar superficie
            # es lo que H17 castigó. Evocar un logograma desde el prompt necesitaría
            # embeddings, que chocan con ADR-003.
            if "logogram" in row.keys() and row["logogram"]:
                lines.append("- el mecanismo, en un signo: **%s**" % row["logogram"])
            if "physical_scene" in row.keys() and row["physical_scene"]:
                lines.append("- el mecanismo, como escena física — es una imagen del "
                             "mecanismo, no del código:")
                lines.append("  %s" % row["physical_scene"])
            if "ideation" in row.keys() and row["ideation"]:
                lines.append("- qué se conserva y qué se pierde: %s"
                             % _recortar(row["ideation"]))
            abiertas, confirmadas, refutadas = _proyectadas(conn, row)
            if abiertas:
                # Lo proyectado se anuncia como proyectado, siempre. Es lo único que se
                # inyecta que **nadie observó**: si el agente no puede distinguirlo de
                # una señal real, dream deja de ser memoria y pasa a ser una fuente de
                # afirmaciones sin origen.
                lines.append("- síntomas **anticipados** por dream desde ese mecanismo "
                             "— NINGUNO fue observado, son conjeturas:")
                for señal in abiertas[:3]:
                    lines.append("  - %s" % señal)
            if confirmadas:
                # Tercera categoría, ni observada ni conjetura suelta. Y sigue pesando la
                # mitad: que el mecanismo haya acertado no vuelve a este trabajo el que
                # lo vio.
                lines.append("- anticipados por dream y después **CONFIRMADOS** por "
                             "alguien que fue a mirar (siguen pesando la mitad: "
                             "confirmarlos no los vuelve observaciones de esta sesión):")
                for señal in confirmadas[:3]:
                    lines.append("  - %s" % señal)
            if refutadas:
                # No se listan: alguien sabe por qué no pueden pasar. Que hubo trabajo ahí
                # sí se dice — es lo que distingue una conjetura descartada de una que
                # nadie miró.
                lines.append("- y %d conjetura(s) de este mecanismo fueron **refutadas** "
                             "y no se listan. `/nightshift:why %s` las muestra."
                             % (refutadas, short))
        # Lo que esta trayectoria reemplazó. Es la mitad de la memoria que más se
        # olvida: sin el camino descartado, dentro de tres semanas alguien lo propone de
        # nuevo y lo recorre entero. Va aunque sea de otro repo — un contraste es
        # abstracción, no detalle.
        for vieja in store.superseded_of(conn, row["id"]):
            contraste = {}
            if "contrast_json" in vieja.keys() and vieja["contrast_json"]:
                try:
                    contraste = json.loads(vieja["contrast_json"]) or {}
                except ValueError:
                    contraste = {}
            if not contraste:
                lines.append("- reemplazó a `%s`, que se descartó (sin contraste "
                             "consolidado)" % vieja["id"][:8])
                continue
            lines.append("- **reemplazó a `%s`**, y esa alternativa NO se borró:"
                         % vieja["id"][:8])
            lines.append("  - qué cambió: %s" % contraste.get("changed", "—"))
            if contraste.get("bought"):
                lines.append("  - qué compró: %s" % contraste["bought"])
            if contraste.get("cost"):
                lines.append("  - qué costó: %s" % contraste["cost"])
            for condicion in (contraste.get("old_valid_when") or [])[:3]:
                lines.append("  - la descartada seguía siendo la correcta cuando: %s"
                             % condicion)

        if otro_repo:
            # Nada de pasos: de otro repo cruza el patrón, no el detalle.
            lines.append("- sólo el patrón: los pasos son de otro repositorio y no cruzan.")
            lines.append("")
            continue
        # Lo que dijo el oráculo de git (plan §7, O2). Va **antes** de los pasos porque
        # cambia cómo se lee todo lo que sigue: una memoria cuyo fix fue revertido sigue
        # enseñando algo, y callarlo sería mentir por omisión.
        corroboracion = store.get_corroboration(row)
        if corroboracion and corroboracion.get("status") in ("reverted", "absent"):
            lines.append("- ⚠ **el fix de esta trayectoria NO sobrevivió** (%s): %s"
                         % (corroboracion["status"], corroboracion.get("evidence") or ""))
            lines.append("  Sigue inyectada porque el camino recorrido enseña igual, pero"
                         " el desenlace no se sostuvo.")
        elif corroboracion and corroboracion.get("status") == "survived":
            # "Corroborada" no es "verificada", y el texto lo dice para que el agente no
            # lo lea como un ascenso: `verify` es M5 y no existe.
            lines.append("- el fix sobrevivió en la historia del repo (corroborado, **no"
                         " verificado**): %s" % (corroboracion.get("evidence") or ""))
        if row["hypothesis"]:
            lines.append("- hipótesis: %s" % row["hypothesis"])
        steps = store.steps_of(conn, row["id"])
        decisive = [s for s in steps if s["decisive"]]
        shown = decisive[:3] or steps[:3]
        for step in shown:
            marker = "**señal decisiva**" if step["decisive"] else step["kind"]
            detail = step["error_message"] or step["result_summary"] or "(sin resumen)"
            lines.append("- %s (`%s`): %s" % (marker, step["tool"] or step["kind"], detail[:200]))
        if row["outcome_result"]:
            lines.append("- desenlace: `%s`" % row["outcome_result"])
        lines.append("- origen completo: `/nightshift:why %s`" % short)
        lines.append("")

    lines.append("_%d trayectoria(s) inyectada(s). `/nightshift:status` para ver el registro._"
                 % len(chosen))
    return "\n".join(lines), chosen
