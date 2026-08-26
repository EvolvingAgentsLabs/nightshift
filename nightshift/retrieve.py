"""Retrieval estructural e inyección en SessionStart (M2).

Sin dream todavía: se inyectan trayectorias crudas recientes del mismo tipo de tarea
(plan §3, M2). El ranking es determinista y cada inyección queda registrada con su
trayectoria origen, para que `/nightshift:why` pueda reconstruirla — que es el gate
de M2 y la condición de éxito 3 de la spec.
"""

from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone

from . import context, store

# Pesos del ranking. Determinista y auditable: `why` los reimprime tal cual.
W_SAME_TASK = 2.0
W_SAME_REPO = 1.0
W_DECISIVE = 1.0
W_TESTS_PASSED = 1.5
W_USER_CORRECTED = -1.0
W_DAY_DECAY = -0.05


def _age_days(created_at: str) -> float:
    try:
        then = datetime.strptime(created_at, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc)
    except ValueError:
        return 999.0
    return max(0.0, (datetime.now(timezone.utc) - then).total_seconds() / 86400.0)


def candidates(conn, *, task_type, repo_fingerprint, cfg, exclude_id=None):
    lookback = cfg.get("retrieval_lookback_days", 30)
    cutoff = (datetime.now(timezone.utc) - timedelta(days=lookback)).strftime("%Y-%m-%dT%H:%M:%SZ")
    rows = conn.execute(
        "SELECT * FROM trajectories WHERE status IN ('closed','candidate','procedure')"
        " AND created_at >= ? ORDER BY created_at DESC LIMIT 200", (cutoff,)).fetchall()

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
        score += W_DAY_DECAY * _age_days(row["created_at"])
        score *= float(row["injection_weight"] or 0.3)

        if score <= 0:
            continue
        scored.append((score, ",".join(reasons) or "recent", row))

    scored.sort(key=lambda item: (-item[0], item[2]["created_at"]))
    return scored


def render(conn, scored, *, max_injected, native_memory, task_type=None):
    """Texto que se inyecta como additionalContext. Vacío si no hay nada que decir.

    `task_type` sólo cambia cómo se presenta el material: decir "del mismo tipo de
    tarea" cuando el tipo todavía es `general` sería describir un ranking que no ocurrió.
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
