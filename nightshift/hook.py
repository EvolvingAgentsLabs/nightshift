"""Punto de entrada de los hooks de Claude Code.

Contrato duro (spec §7.2): **nightshift nunca bloquea una sesión.** Cualquier
excepción se traga, se loguea y el proceso sale 0 sin inyectar nada. Una sesión con
nightshift roto debe ser indistinguible de una sesión sin nightshift.

Eventos verificados contra https://code.claude.com/docs/en/hooks el 2026-08-26.
Dos correcciones al plan v0.3 §2, ambas documentadas en la spec:

- `PostToolUse` no dispara en fallos: van a `PostToolUseFailure` (spec §5.2).
- `Stop` dispara al terminar **cada turno**, no la sesión. Sella el turno; quien cierra
  la trayectoria es `SessionEnd` (spec §5.6).
"""

from __future__ import annotations

import json
import sys
import traceback

from . import config, context, retrieve, store
from .redact import Redactor

EVENTS = ("SessionStart", "UserPromptSubmit", "PostToolUse", "PostToolUseFailure",
          "PreCompact", "Stop", "SessionEnd")

# Nombres de campo del payload, verificados contra Claude Code el 2026-08-26 sondeando
# los hooks de verdad (spec §5.9). Se leen con alternativa porque cambian entre
# versiones, y la primera versión de esto leyó los que **no** eran: el prompt nunca
# llegaba, así que el tipo de tarea nunca se clasificaba y ninguna corrección se
# detectaba — en silencio, porque los hooks salen 0 pase lo que pase.
CAMPO_PROMPT = ("prompt", "user_input")
CAMPO_SALIDA = ("tool_response", "tool_output")
CAMPO_ERROR = ("error", "error_message")


# Lo que trae el `tool_response` según la tool, verificado el 2026-08-26 sobre capturas
# reales: Bash devuelve {stdout, stderr, interrupted, isImage, noOutputExpected} y Read
# devuelve {type, file:{filePath, content, …}}.
CLAVES_DE_SALIDA = ("stdout", "content", "output", "result", "message")
CLAVES_DE_RUIDO = ("isImage", "noOutputExpected", "interrupted", "type", "gitOperation",
                   "filePath", "numLines", "startLine", "totalLines", "userModified",
                   "replaceAll", "structuredPatch", "originalFile")


def resumir_salida(raw, profundidad=0):
    """Saca el texto que importa del `tool_response`. Determinista, sin modelo.

    Guardar el JSON crudo gastaba el presupuesto de caracteres en andamiaje: en una
    captura real el resumen empezaba con `{"stdout": "…", "isImage": false,
    "noOutputExpected": false}` y la salida verdadera quedaba cortada por el límite. La
    memoria que se inyecta es lo que el agente lee: si son llaves y flags, no es memoria.
    """
    if raw is None:
        return ""
    if isinstance(raw, str):
        return raw
    if isinstance(raw, list):
        partes = [resumir_salida(item, profundidad + 1) for item in raw[:10]]
        return "\n".join(p for p in partes if p)
    if isinstance(raw, dict) and profundidad <= 3:
        # Una edición: lo que importa es el cambio, no una de las dos mitades. Sondeando
        # las tools de verdad, `Edit` devolvía `oldString` y el resumen quedaba diciendo
        # que la edición había producido el texto que **borró**.
        if "oldString" in raw and "newString" in raw:
            viejo = str(raw.get("oldString") or "").strip()
            nuevo = str(raw.get("newString") or "").strip()
            return "reemplazó «%s» por «%s»" % (viejo[:120], nuevo[:120])
        for clave in CLAVES_DE_SALIDA:
            valor = raw.get(clave)
            texto = resumir_salida(valor, profundidad + 1) if valor is not None else ""
            if texto.strip():
                extra = resumir_salida(raw.get("stderr"), profundidad + 1) \
                    if clave == "stdout" else ""
                return "%s\n%s" % (texto, extra.strip()) if extra.strip() else texto
        # `file` de Read: el contenido está un nivel más abajo.
        for clave, valor in raw.items():
            if clave in CLAVES_DE_RUIDO or valor is None:
                continue
            texto = resumir_salida(valor, profundidad + 1)
            if texto.strip():
                return texto
        return ""
    return json.dumps(raw, ensure_ascii=False)


def _primero(payload, claves, default=None):
    """Primer campo presente de la lista. Los nombres cambian entre versiones."""
    for clave in claves:
        if payload.get(clave) is not None:
            return payload[clave]
    return default


def _log(message: str) -> None:
    try:
        path = config.log_path()
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("a", encoding="utf-8") as handle:
            handle.write("%s %s\n" % (store.now(), message))
    except Exception:
        pass


def _emit(event: str, additional_context: str = "", system_message: str = "") -> None:
    payload = {"hookEventName": event}
    if additional_context:
        payload["additionalContext"] = additional_context
    if system_message:
        payload["systemMessage"] = system_message
    if len(payload) == 1:
        return
    sys.stdout.write(json.dumps({"hookSpecificOutput": payload}, ensure_ascii=False))


def _redactor(cwd: str, cfg: dict) -> Redactor:
    from pathlib import Path
    return Redactor(identifiers=context.repo_identifiers(cwd),
                    deny_paths=cfg.get("deny_paths", []),
                    home_dir=str(Path.home()))


def _ensure_trajectory(conn, payload, cfg):
    session_id = payload.get("session_id")
    if not session_id:
        return None
    row = store.active_trajectory(conn, session_id)
    if row is not None:
        return row["id"]
    cwd = payload.get("cwd") or "."
    red = _redactor(cwd, cfg)
    return store.open_trajectory(
        conn,
        session_id=session_id,
        repo_fingerprint=context.repo_fingerprint(cwd),
        task_type=context.DEFAULT_TASK_TYPE,
        harness_version=payload.get("version"),
        base_commit=context.base_commit(cwd),
        redaction=red.report(),
    )


# ------------------------------------------------------------------- huérfanas
def _close_orphans(conn, cfg, session_id):
    """Cierra las trayectorias `open` que quedaron de sesiones muertas.

    Si una sesión muere sin `SessionEnd` — un `Ctrl-C` duro, un crash — su trayectoria
    queda `open` para siempre, y el retrieval sólo mira `closed`/`candidate`/`procedure`:
    se pierde entera. Una huérfana con pasos vale más cerrada que perdida.

    El corte es por **falta de actividad**, nunca por antigüedad, y nunca toca la sesión
    en curso: dos sesiones simultáneas son normales, y cerrarle la trayectoria a la que
    sigue viva la partiría en dos.
    """
    hours = float(cfg.get("orphan_after_hours") or 0)
    if hours <= 0:
        return []
    rows = store.stale_open_trajectories(conn, cutoff=store.hours_ago(hours),
                                         exclude_session=session_id)
    closed = []
    for row in rows:
        result, evidence = _infer_outcome(conn, row["id"])
        note = "huérfana: sin actividad en más de %gh, cerrada por otra sesión" % hours
        store.close_trajectory(conn, row["id"], result=result,
                               evidence=("%s · %s" % (note, evidence)) if evidence else note)
        _log("huérfana %s cerrada como %s" % (row["id"], result))
        closed.append((row["id"], result))
    return closed


# ---------------------------------------------------------- retrieval e inyección
def _retrieve_and_inject(conn, payload, cfg, tid, task_type, prompt=None):
    """Rankea, renderiza y registra. Lo comparten `SessionStart` y `UserPromptSubmit`.

    Nada que ya se haya inyectado en esta sesión se vuelve a inyectar: el retrieval
    corre dos veces y la misma trayectoria dicha dos veces no es más evidencia, es más
    contexto gastado.
    """
    cwd = payload.get("cwd") or "."
    session_id = payload.get("session_id")
    fingerprint = context.repo_fingerprint(cwd)
    scored = retrieve.candidates(
        conn,
        task_type=task_type,
        repo_fingerprint=fingerprint,
        cfg=cfg,
        exclude_id=tid,
        # El texto del prompt sólo existe acá. Se usa para enganchar por síntoma y no se
        # persiste: lo que queda en el registro es el motivo, no las palabras.
        prompt=prompt,
    )
    if session_id:
        ya = store.injected_sources(conn, session_id)
        scored = [item for item in scored if item[2]["id"] not in ya]
    text, chosen = retrieve.render(conn, scored, max_injected=cfg.get("max_injected", 3),
                                   native_memory=context.memory_signal(cwd),
                                   task_type=task_type, repo_fingerprint=fingerprint)
    for rank, (score, reasons, source) in enumerate(chosen, start=1):
        store.record_injection(conn, session_id=session_id, source_trajectory=source["id"],
                               rank=rank, score=score, reason=reasons, into_trajectory=tid)
    return text, chosen


# ------------------------------------------------------------------- SessionStart
def on_session_start(payload, cfg, conn):
    cwd = payload.get("cwd") or "."
    # Antes de abrir la de esta sesión y antes de rankear: una huérfana recién cerrada es
    # material recuperable en esta misma sesión.
    orphans = _close_orphans(conn, cfg, payload.get("session_id"))
    tid = _ensure_trajectory(conn, payload, cfg)
    row = store.get_trajectory(conn, tid) if tid else None
    # Acá el tipo de tarea es siempre `general`: SessionStart corre antes de que el
    # usuario escriba. El segundo retrieval, en el primer prompt, es el estructural.
    text, chosen = _retrieve_and_inject(
        conn, payload, cfg, tid,
        row["task_type"] if row else context.DEFAULT_TASK_TYPE)

    # `additionalContext` va al contexto del modelo y el usuario no lo ve. Sin una línea
    # visible, un plugin que funciona y uno que no hace nada se ven exactamente igual.
    if chosen:
        message = ("nightshift: %d trayectoria(s) sin verificar inyectada(s) · "
                   "/nightshift:status" % len(chosen))
    else:
        message = "nightshift: capturando · sin memoria previa para este tipo de tarea"
    if orphans:
        message += " · %d huérfana(s) cerrada(s)" % len(orphans)
    return text, message


# -------------------------------------------------------------- UserPromptSubmit
def on_user_prompt_submit(payload, cfg, conn):
    """Sólo dos cosas: detectar correcciones y fijar el tipo de tarea.

    El texto del prompt **no se persiste**. Se guarda la etiqueta de clasificación, que
    sale de un enum fijo (`context.TASK_TYPE_RULES`), no del prompt.
    """
    tid = _ensure_trajectory(conn, payload, cfg)
    if not tid:
        return ""
    prompt = _primero(payload, CAMPO_PROMPT, "") or ""

    if context.CORRECTION_RE.search(prompt):
        idx = store.mark_last_contradicted(conn, tid)
        if idx is not None:
            _log("contradicted step %s of %s" % (idx, tid))

    row = store.get_trajectory(conn, tid)
    if row is None or row["task_type"] != context.DEFAULT_TASK_TYPE:
        return ""
    task_type = context.classify_task(prompt)
    if task_type == context.DEFAULT_TASK_TYPE:
        return ""
    conn.execute("UPDATE trajectories SET task_type = ? WHERE id = ?", (task_type, tid))
    conn.commit()

    # Segundo retrieval, ahora sí por estructura. Es la primera vez en la sesión que hay
    # tipo de tarea, y por lo tanto la primera vez que "retrieve por tipo de tarea"
    # (spec §5.7) puede cumplirse. Ocurre una sola vez: en el próximo prompt el tipo ya
    # no es `general` y esta rama no se vuelve a tomar.
    text, chosen = _retrieve_and_inject(conn, payload, cfg, tid, task_type, prompt=prompt)
    if not chosen:
        return ""
    _log("retrieval por tipo de tarea (%s): %d inyectada(s)" % (task_type, len(chosen)))
    return text, ("nightshift: %d trayectoria(s) de `%s` inyectada(s) · /nightshift:status"
                  % (len(chosen), task_type))


# ------------------------------------------------------- PostToolUse / …Failure
def _append_tool_step(payload, cfg, conn, *, failed):
    tid = _ensure_trajectory(conn, payload, cfg)
    if not tid:
        return ""
    cwd = payload.get("cwd") or "."
    red = _redactor(cwd, cfg)

    native = payload.get("tool_name")
    tool = context.normalize_tool(native)
    raw_args = payload.get("tool_input") or {}

    # Un tool call que toca un deny_path no se captura en absoluto: ni argumentos, ni
    # resultado, ni el hecho de que ocurrió (spec §8.1). Sólo se cuenta.
    if red.touches_denied(raw_args):
        _bump_deny_hits(conn, tid, 1)
        return ""

    args = red.obj(raw_args)

    limit = cfg.get("max_result_summary_chars", 400)
    if failed:
        summary = None
        error = (red.text(str(_primero(payload, CAMPO_ERROR, "") or "")) or "")[:limit]
    else:
        raw = resumir_salida(_primero(payload, CAMPO_SALIDA))
        summary = (red.text(raw) or "")[:limit]
        error = None

    # Heurística determinista de señal decisiva: un fallo de tool, o un comando de test
    # que pasa. Documentada en spec §4.3.
    #
    # Salvo una interrupción: `is_interrupt` significa que el usuario cortó, no que la
    # herramienta falló. Tratarlo como señal decisiva sería aprender del momento en que
    # alguien apretó Esc.
    decisive = bool(failed) and not payload.get("is_interrupt")
    if not failed and tool == "run_shell":
        command = str((payload.get("tool_input") or {}).get("command", ""))
        if context.TEST_CMD_RE.search(command):
            decisive = True

    store.append_step(conn, tid,
                      kind="tool_failure" if failed else "tool_use",
                      tool=tool, tool_native=native,
                      tool_use_id=payload.get("tool_use_id"),
                      args=args, result_summary=summary, error_message=error,
                      decisive=decisive,
                      max_steps=cfg.get("max_steps_per_trajectory", 400))

    _merge_redaction(conn, tid, red.report())
    return ""


def _merge_redaction(conn, tid, report):
    row = store.get_trajectory(conn, tid)
    if row is None:
        return
    current = json.loads(row["redaction_json"])
    merged = dict(report)
    merged["deny_path_hits"] = (current.get("deny_path_hits", 0)
                                + report.get("deny_path_hits", 0))
    merged["rules_applied"] = sorted(set(current.get("rules_applied", []))
                                     | set(report.get("rules_applied", [])))
    conn.execute("UPDATE trajectories SET redaction_json = ? WHERE id = ?",
                 (json.dumps(merged), tid))
    conn.commit()


def _bump_deny_hits(conn, tid, n):
    _merge_redaction(conn, tid, {"redactor_version": None, "deny_path_hits": n,
                                 "rules_applied": []})
    row = store.get_trajectory(conn, tid)
    data = json.loads(row["redaction_json"])
    if data.get("redactor_version") is None:
        from .redact import REDACTOR_VERSION
        data["redactor_version"] = REDACTOR_VERSION
        conn.execute("UPDATE trajectories SET redaction_json = ? WHERE id = ?",
                     (json.dumps(data), tid))
        conn.commit()


def on_post_tool_use(payload, cfg, conn):
    return _append_tool_step(payload, cfg, conn, failed=False)


def on_post_tool_use_failure(payload, cfg, conn):
    return _append_tool_step(payload, cfg, conn, failed=True)


# ---------------------------------------------------------------------- PreCompact
def on_pre_compact(payload, cfg, conn):
    """Señal de sellado, no fuente de datos.

    El payload no trae el transcript (spec §5.3): sólo session_id, cwd y
    compaction_reason. Lo que no se capturó paso a paso ya está perdido, así que acá
    sólo se marca el corte.
    """
    tid = _ensure_trajectory(conn, payload, cfg)
    if not tid:
        return ""
    reason = payload.get("compaction_reason") or "unknown"
    count = len(store.steps_of(conn, tid))
    store.append_step(conn, tid, kind="compact_snapshot",
                      result_summary="sellado antes de compactar (%s), %d pasos acumulados"
                                     % (reason, count),
                      max_steps=cfg.get("max_steps_per_trajectory", 400))
    return ""


# ----------------------------------------------------------------- Stop / SessionEnd
def _infer_outcome(conn, tid):
    steps = store.steps_of(conn, tid)
    if not steps:
        return "abandoned", None
    if any(s["contradicted"] for s in steps):
        return "user_corrected", "el usuario corrigió un paso"
    passed = [s for s in steps if s["decisive"] and s["kind"] == "tool_use"
              and s["tool"] == "run_shell"]
    if passed:
        return "tests_passed", "comando de test decisivo con salida 0"
    return "unknown", None


def on_stop(payload, cfg, conn):
    """Sella el turno. NO cierra la trayectoria: Stop dispara por turno (spec §5.6)."""
    tid = _ensure_trajectory(conn, payload, cfg)
    if not tid:
        return ""
    result, _ = _infer_outcome(conn, tid)
    store.append_step(conn, tid, kind="observation",
                      result_summary="fin de turno · señal acumulada: %s" % result,
                      max_steps=cfg.get("max_steps_per_trajectory", 400))
    return ""


def on_session_end(payload, cfg, conn):
    session_id = payload.get("session_id")
    if not session_id:
        return ""
    row = store.active_trajectory(conn, session_id)
    if row is None:
        return ""
    result, evidence = _infer_outcome(conn, row["id"])
    store.close_trajectory(conn, row["id"], result=result, evidence=evidence)
    _log("closed %s as %s" % (row["id"], result))
    return ""


HANDLERS = {
    "SessionStart": on_session_start,
    "UserPromptSubmit": on_user_prompt_submit,
    "PostToolUse": on_post_tool_use,
    "PostToolUseFailure": on_post_tool_use_failure,
    "PreCompact": on_pre_compact,
    "Stop": on_stop,
    "SessionEnd": on_session_end,
}


def dispatch(event: str, payload: dict):
    """Devuelve `(additional_context, system_message)`.

    Los dos van a lugares distintos: `additionalContext` al contexto del modelo,
    `systemMessage` a la pantalla del usuario. Confundirlos es la razón por la que un
    plugin que funciona puede parecer muerto.
    """
    cfg = config.load()
    if not (cfg["configured"] and cfg["enabled"] and cfg["deny_paths"]):
        if event == "SessionStart":
            return ("nightshift está instalado pero **no configurado**: no captura nada "
                    "hasta que exista `deny_paths` (spec §8.1).\n\n"
                    "Falta `%s`. Corré `nightshift init` y después `/reload-plugins`."
                    % config.config_path(),
                    "nightshift: NO configurado, no captura nada · corré `nightshift init`")
        return "", ""
    handler = HANDLERS.get(event)
    if handler is None:
        return "", ""
    conn = store.connect()
    try:
        result = handler(payload, cfg, conn)
        if isinstance(result, tuple):
            return (result[0] or ""), (result[1] or "")
        return (result or ""), ""
    finally:
        conn.close()


def main(argv=None) -> int:
    argv = list(argv if argv is not None else sys.argv[1:])
    event = argv[0] if argv else ""
    try:
        raw = sys.stdin.read()
        payload = json.loads(raw) if raw.strip() else {}
        if not isinstance(payload, dict):
            payload = {}
        text, message = dispatch(event, payload)
        if text or message:
            _emit(event, additional_context=text, system_message=message)
    except Exception:
        # Nunca bloquear la sesión. Nunca escribir a stdout algo que no sea JSON válido.
        _log("hook %s falló:\n%s" % (event, traceback.format_exc()))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
