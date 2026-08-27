"""Retrieval estructural e inyección en SessionStart (M2).

Sin dream todavía: se inyectan trayectorias crudas recientes del mismo tipo de tarea
(plan §3, M2). El ranking es determinista y cada inyección queda registrada con su
trayectoria origen, para que `/nightshift:why` pueda reconstruirla — que es el gate
de M2 y la condición de éxito 3 de la spec.
"""

from __future__ import annotations

import json
import re
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

# Cuántas palabras de contenido tienen que coincidir para llamarlo enganche. Con una
# sola, "test" alcanza para hermanar cualquier par de trayectorias de este repo.
MIN_TOKENS_EN_COMUN = 2

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


def _tokens(texto):
    """Palabras de contenido, normalizadas. Determinista y sin dependencias.

    Se sacan los acentos porque "análisis" y "analisis" son la misma palabra para esto, y
    una coincidencia que depende de cómo alguien escribió una tilde no es estructural.
    """
    if not texto:
        return frozenset()
    plano = unicodedata.normalize("NFKD", texto.lower())
    plano = "".join(c for c in plano if not unicodedata.combining(c))
    return frozenset(t for t in _PALABRA_RE.findall(plano) if t not in _VACIAS)


def _enganche(tokens_prompt, frases):
    """¿Alguna de estas frases habla de lo mismo que el prompt?

    Devuelve la cantidad de palabras de contenido en común de la frase que más comparte.
    Cero es "no engancha".
    """
    if not tokens_prompt:
        return 0
    mejor = 0
    for frase in frases or ():
        comunes = len(tokens_prompt & _tokens(frase))
        if comunes > mejor:
            mejor = comunes
    return mejor if mejor >= MIN_TOKENS_EN_COMUN else 0


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
            if _enganche(tokens_prompt, senales):
                score += W_SIGNAL_MATCH
                reasons.append("signal_match")
            proyectadas = _proyectadas(row)
            if proyectadas and _enganche(tokens_prompt, proyectadas):
                score += W_PROJECTED_MATCH
                reasons.append("projected_match")
        score += W_DAY_DECAY * _age_days(row["created_at"])
        score *= float(row["injection_weight"] or 0.3)

        if score <= 0:
            continue
        scored.append((score, ",".join(reasons) or "recent", row))

    scored.sort(key=lambda item: (-item[0], item[2]["created_at"]))
    return scored


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


def _proyectadas(row):
    """Síntomas que dream anticipó y nadie observó. Vacío si la fila es vieja.

    La columna se agrega por migración, así que una fila consolidada antes de ADR-004 no
    la tiene: `row.keys()` es el guard y no un `try` alrededor de todo.
    """
    if "projected_signals_json" not in row.keys() or not row["projected_signals_json"]:
        return []
    try:
        datos = json.loads(row["projected_signals_json"])
    except (TypeError, ValueError):
        return []
    return [x for x in datos if isinstance(x, str)] if isinstance(datos, list) else []


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
            if "ideation" in row.keys() and row["ideation"]:
                lines.append("- qué se conserva y qué se pierde: %s"
                             % _recortar(row["ideation"]))
            proyectadas = _proyectadas(row)
            if proyectadas:
                # Lo proyectado se anuncia como proyectado, siempre. Es lo único que se
                # inyecta que **nadie observó**: si el agente no puede distinguirlo de
                # una señal real, dream deja de ser memoria y pasa a ser una fuente de
                # afirmaciones sin origen.
                lines.append("- síntomas **anticipados** por dream desde ese mecanismo "
                             "— NINGUNO fue observado, son conjeturas:")
                for señal in proyectadas[:3]:
                    lines.append("  - %s" % señal)
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
