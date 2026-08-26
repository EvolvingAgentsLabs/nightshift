"""CLI de nightshift: `nightshift <subcomando>` (o `python3 -m nightshift`).

Las skills del plugin son envoltorios finos sobre estos subcomandos. La lógica vive
acá para que se pueda testear sin un harness corriendo.
"""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path

from . import __version__, config, context, store
from .redact import Redactor

PLUGIN_ROOT = Path(os.environ.get("CLAUDE_PLUGIN_ROOT") or Path(__file__).resolve().parent.parent)


# --------------------------------------------------------------------------- init
def cmd_init(args) -> int:
    path = config.init(force=args.force)
    cfg = config.load()
    print("config: %s" % path)
    print("deny_paths: %d patrones" % len(cfg["deny_paths"]))
    print("store: %s" % config.db_path())
    print("captura: %s" % ("activa" if config.is_enabled() else "INACTIVA"))
    return 0


# ------------------------------------------------------------------------- status
def cmd_status(args) -> int:
    if not config.config_path().is_file():
        print("nightshift no está configurado. Corré `nightshift init`.")
        print("Sin `deny_paths` resuelto no se captura nada (spec §8.1).")
        return 0
    conn = store.connect()
    try:
        c = store.counts(conn)
        print("nightshift %s · milestone M1+M2 (capture + retrieve)" % __version__)
        print("store: %s" % config.db_path())
        print()
        print("trayectorias:")
        for status in ("open", "closed", "candidate", "procedure", "superseded", "discarded"):
            print("  %-11s %d" % (status, c[status]))
        print("  %-11s %d" % ("pasos", c["steps"]))
        print("  %-11s %d" % ("inyecciones", c["injections"]))
        print()
        print("dream todavía no existe: nada llega a `candidate` ni a `procedure`.")
        print("Lo que se inyecta son trayectorias crudas (M2).")
        rows = conn.execute(
            "SELECT * FROM trajectories ORDER BY created_at DESC LIMIT ?", (args.limit,)).fetchall()
        if rows:
            print()
            print("últimas trayectorias:")
            for row in rows:
                print("  %s  %-20s %-9s %s  pasos=%d" % (
                    row["id"][:8], row["task_type"], row["status"], row["created_at"],
                    len(store.steps_of(conn, row["id"]))))
        inj = conn.execute("SELECT * FROM injections ORDER BY at DESC LIMIT ?",
                           (args.limit,)).fetchall()
        if inj:
            print()
            print("últimas inyecciones:")
            for row in inj:
                print("  %s  <- %s  rank=%d score=%.2f  %s" % (
                    row["at"], row["source_trajectory"][:8], row["rank"], row["score"],
                    row["reason"]))
        return 0
    finally:
        conn.close()


# ---------------------------------------------------------------------------- why
def cmd_why(args) -> int:
    """Reconstruye la trayectoria origen. Gate de M2 y condición de éxito 3."""
    conn = store.connect()
    try:
        row = store.get_trajectory(conn, args.trajectory_id)
        if row is None:
            print("no encontrada: %s" % args.trajectory_id, file=sys.stderr)
            return 1
        print("trayectoria %s" % row["id"])
        print("  tipo de tarea : %s" % row["task_type"])
        print("  estado        : %s" % row["status"])
        print("  abierta       : %s" % row["created_at"])
        print("  cerrada       : %s" % (row["closed_at"] or "—"))
        print("  repo          : %s (fingerprint)" % row["repo_fingerprint"][:16])
        print("  base_commit   : %s" % (row["base_commit"] or "—"))
        print("  desenlace     : %s" % (row["outcome_result"] or "—"))
        print("  verificada    : %s" % ("sí" if row["verified_json"] else
                                        "no — dream fase 2 no existe todavía (M5)"))
        print("  redacción     : %s" % row["redaction_json"])
        print()
        print("pasos:")
        for step in store.steps_of(conn, row["id"]):
            flags = []
            if step["decisive"]:
                flags.append("DECISIVO")
            if step["contradicted"]:
                flags.append("CONTRADICHO")
            detail = step["error_message"] or step["result_summary"] or ""
            print("  [%3d] %-16s %-11s %s%s" % (
                step["idx"], step["kind"], step["tool"] or "—", detail[:110],
                (" <%s>" % ",".join(flags)) if flags else ""))
        inj = store.injections_of_source(conn, row["id"])
        print()
        if inj:
            print("se inyectó en %d sesión(es):" % len(inj))
            for item in inj:
                print("  %s  sesión=%s rank=%d score=%.2f  motivo=%s" % (
                    item["at"], (item["session_id"] or "—")[:12], item["rank"],
                    item["score"], item["reason"]))
        else:
            print("nunca se inyectó.")
        return 0
    finally:
        conn.close()


# ------------------------------------------------------------------------- export
def cmd_export(args) -> int:
    conn = store.connect()
    try:
        doc = store.export_trajectory(conn, args.trajectory_id)
        if doc is None:
            print("no encontrada: %s" % args.trajectory_id, file=sys.stderr)
            return 1
        json.dump(doc, sys.stdout, indent=2, ensure_ascii=False)
        sys.stdout.write("\n")
        return 0
    finally:
        conn.close()


# ------------------------------------------------------------------------- doctor
def _check(name, ok, detail=""):
    return {"name": name, "ok": bool(ok), "detail": detail}


def run_doctor() -> list[dict]:
    """Auto-diagnóstico en runtime. Cada ítem es una aserción sobre una invariante."""
    checks = []

    checks.append(_check("python >= 3.9", sys.version_info >= (3, 9),
                         ".".join(str(p) for p in sys.version_info[:3])))

    cfg_ok = config.config_path().is_file()
    checks.append(_check("config presente", cfg_ok,
                         str(config.config_path()) if cfg_ok
                         else "no existe: corré `nightshift init`"))

    # Sonda: el store tiene que ser el mismo lo ejecute quien lo ejecute. Claude Code
    # le pasa CLAUDE_PLUGIN_DATA a los hooks pero no al Bash tool; si influyera en la
    # ruta habría dos stores, y la captura nunca arrancaría.
    resolved = str(config.home())
    saved = os.environ.get("CLAUDE_PLUGIN_DATA")
    os.environ["CLAUDE_PLUGIN_DATA"] = "/tmp/nightshift-probe-debe-ser-ignorado"
    try:
        ignored = str(config.home()) == resolved
    finally:
        if saved is None:
            os.environ.pop("CLAUDE_PLUGIN_DATA", None)
        else:
            os.environ["CLAUDE_PLUGIN_DATA"] = saved
    checks.append(_check("un solo store para hooks y CLI", ignored, resolved))

    cfg = config.load()
    checks.append(_check("deny_paths resuelto", bool(cfg["deny_paths"]),
                         "%d patrones" % len(cfg["deny_paths"])))
    checks.append(_check("captura activa", config.is_enabled(),
                         "sin config no se captura (spec §8.1)"))

    # Invariante de coexistencia: el guard debe rechazar el árbol de Auto Memory.
    try:
        config.guard_path(Path.home() / ".claude/projects/foo/memory/MEMORY.md")
        checks.append(_check("guard de Auto Memory", False, "NO rechazó una ruta de memoria"))
    except PermissionError:
        checks.append(_check("guard de Auto Memory", True, "rechaza escrituras (spec §1.3.4)"))

    # El store no puede vivir bajo el árbol de Auto Memory ni dentro del repo.
    db = str(config.db_path())
    checks.append(_check("store fuera de Auto Memory",
                         "/.claude/projects/" not in db, db))

    try:
        conn = store.connect()
        c = store.counts(conn)
        conn.close()
        checks.append(_check("store escribible", True,
                             "%d trayectorias, %d pasos" % (
                                 sum(c[k] for k in ("open", "closed", "candidate", "procedure",
                                                    "superseded", "discarded")), c["steps"])))
    except Exception as exc:
        checks.append(_check("store escribible", False, str(exc)))

    # Canario del redactor: un secreto no puede sobrevivir a la redacción.
    canary = 'API_TOKEN="tok_live_canary_1234567890" en /home/x/proj/src/a.py'
    red = Redactor(identifiers=["proj"], deny_paths=cfg["deny_paths"], home_dir="/home/x")
    out = red.text(canary)
    checks.append(_check("redactor: el secreto no sobrevive",
                         "tok_live_canary_1234567890" not in out, out))
    checks.append(_check("redactor determinista",
                         red.text(canary) == out, "misma entrada, misma salida"))
    denied = red.is_denied("/home/x/proj/.env")
    checks.append(_check("deny_paths bloquea .env", denied, "/home/x/proj/.env"))

    manifest = PLUGIN_ROOT / ".claude-plugin" / "plugin.json"
    hooks = PLUGIN_ROOT / "hooks" / "hooks.json"
    checks.append(_check("manifiesto del plugin", manifest.is_file(), str(manifest)))
    if hooks.is_file():
        try:
            data = json.loads(hooks.read_text(encoding="utf-8"))
            events = set(data.get("hooks", {}))
            from .hook import EVENTS
            unknown = events - set(EVENTS)
            checks.append(_check("hooks declarados conocidos", not unknown,
                                 "eventos: %s" % ", ".join(sorted(events))))
        except ValueError as exc:
            checks.append(_check("hooks.json parseable", False, str(exc)))
    else:
        checks.append(_check("hooks.json presente", False, str(hooks)))

    return checks


def cmd_doctor(args) -> int:
    checks = run_doctor()
    if args.json:
        json.dump(checks, sys.stdout, indent=2, ensure_ascii=False)
        sys.stdout.write("\n")
    else:
        print("nightshift doctor · %s" % __version__)
        print("plugin root: %s" % PLUGIN_ROOT)
        print()
        for item in checks:
            print("  %s  %-34s %s" % ("ok  " if item["ok"] else "FALLA", item["name"],
                                      item["detail"]))
        bad = [c for c in checks if not c["ok"]]
        print()
        print("doctor: %s" % ("OK" if not bad else "%d fallo(s)" % len(bad)))
    return 0 if all(c["ok"] for c in checks) else 1


# ----------------------------------------------------------------------- selftest
REPLAY = [
    ("SessionStart", {"session_id": "selftest", "cwd": "."}),
    ("UserPromptSubmit", {"session_id": "selftest", "cwd": ".",
                          "user_input": "los tests fallan con UnicodeDecodeError"}),
    ("PostToolUse", {"session_id": "selftest", "cwd": ".", "tool_name": "Read",
                     "tool_use_id": "t1", "tool_input": {"file_path": "/tmp/x/parser.py"},
                     "tool_output": "def parse(data): ..."}),
    ("PostToolUseFailure", {"session_id": "selftest", "cwd": ".", "tool_name": "Bash",
                            "tool_use_id": "t2",
                            "tool_input": {"command": "pytest -q",
                                           "env": {"API_TOKEN": "tok_live_selftest_999"}},
                            "error_message": "UnicodeDecodeError: 'utf-8' codec can't decode"}),
    ("PreCompact", {"session_id": "selftest", "cwd": ".", "compaction_reason": "auto"}),
    ("Stop", {"session_id": "selftest", "cwd": ".", "last_assistant_message": "listo"}),
    ("SessionEnd", {"session_id": "selftest", "cwd": "."}),
]


def cmd_selftest(args) -> int:
    """Replay end-to-end de los 7 hooks en un store desechable.

    No toca el store real: usa un NIGHTSHIFT_HOME temporal. Es la prueba de que el
    plugin funciona en esta máquina, no de que el código compila.
    """
    from . import hook

    failures = []
    with tempfile.TemporaryDirectory(prefix="nightshift-selftest-") as tmp:
        previous = os.environ.get("NIGHTSHIFT_HOME")
        os.environ["NIGHTSHIFT_HOME"] = tmp
        try:
            config.init(force=True)
            for event, payload in REPLAY:
                text, message = hook.dispatch(event, payload)
                extra = "  (inyectó %d chars)" % len(text) if text else ""
                extra += "  [%s]" % message if message else ""
                print("  %-20s ok%s" % (event, extra))
            conn = store.connect()
            try:
                rows = conn.execute("SELECT * FROM trajectories").fetchall()
                if len(rows) != 1:
                    failures.append("esperaba 1 trayectoria, hay %d" % len(rows))
                else:
                    row = rows[0]
                    if row["task_type"] != "debug_test_failure":
                        failures.append("task_type = %s" % row["task_type"])
                    if row["status"] != "closed":
                        failures.append("status = %s (SessionEnd no cerró)" % row["status"])
                    doc = store.export_trajectory(conn, row["id"])
                    blob = json.dumps(doc, ensure_ascii=False)
                    if "tok_live_selftest_999" in blob:
                        failures.append("FUGA: el secreto sobrevivió a la redacción")
                    kinds = [s["kind"] for s in doc["steps"]]
                    for expected in ("tool_use", "tool_failure", "compact_snapshot", "observation"):
                        if expected not in kinds:
                            failures.append("falta un paso de tipo %s" % expected)
                    if not any(s["decisive"] for s in doc["steps"]):
                        failures.append("ningún paso quedó marcado como decisivo")
                    out = Path(args.dump) if args.dump else None
                    if out:
                        out.write_text(json.dumps(doc, indent=2, ensure_ascii=False) + "\n",
                                       encoding="utf-8")
                        print("  dump: %s" % out)
            finally:
                conn.close()
        finally:
            if previous is None:
                os.environ.pop("NIGHTSHIFT_HOME", None)
            else:
                os.environ["NIGHTSHIFT_HOME"] = previous

    print()
    if failures:
        for item in failures:
            print("  FALLA  %s" % item)
        print("selftest: %d fallo(s)" % len(failures))
        return 1
    print("selftest: OK — 7 hooks, trayectoria cerrada, sin fuga")
    return 0


# --------------------------------------------------------------------------- dev
def cmd_dev(args) -> int:
    """Estado de desarrollo del propio plugin. Lo usa la skill `/nightshift:dev`."""
    root = PLUGIN_ROOT
    print("nightshift %s" % __version__)
    print("plugin root : %s" % root)
    print("modo dev    : %s" % ("sí — el plugin es este repo"
                                if (root / ".claude-plugin" / "plugin.json").is_file()
                                else "no"))
    print("cargado como: %s" % ("plugin (CLAUDE_PLUGIN_ROOT presente)"
                                if os.environ.get("CLAUDE_PLUGIN_ROOT")
                                else "CLI suelta (sin CLAUDE_PLUGIN_ROOT)"))
    print("store       : %s" % config.db_path())
    print("captura     : %s" % ("activa" if config.is_enabled() else "INACTIVA (nightshift init)"))
    branch = context._git(str(root), "rev-parse", "--abbrev-ref", "HEAD")
    head = context._git(str(root), "rev-parse", "--short", "HEAD")
    dirty = context._git(str(root), "status", "--porcelain")
    print("git         : %s @ %s%s" % (branch or "?", head or "?",
                                       " (sucio)" if dirty else " (limpio)"))
    print()
    print("milestone actual: M1+M2 — capture + retrieve")
    print("  hecho     : hooks de captura, redactor, store, retrieval, /why")
    print("  falta     : M3 dream + scheduler, M4 benchmark (go/no-go), M5 verify")
    print("  prohibido : empezar M5 antes del veredicto de M4; adapter de OpenCode;")
    print("              escribir en el árbol de Auto Memory; dependencias remotas")
    print()
    print("gate: make check   (lint-docs + lint-code + validate-schema + test + selftest)")
    return 0


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(prog="nightshift", description=__doc__)
    parser.add_argument("--version", action="version", version=__version__)
    sub = parser.add_subparsers(dest="cmd", required=True)

    p = sub.add_parser("init", help="crear la config con deny_paths por defecto")
    p.add_argument("--force", action="store_true")
    p.set_defaults(func=cmd_init)

    p = sub.add_parser("status", help="qué hay capturado y qué se inyectó")
    p.add_argument("--limit", type=int, default=10)
    p.set_defaults(func=cmd_status)

    p = sub.add_parser("why", help="reconstruir la trayectoria origen")
    p.add_argument("trajectory_id")
    p.set_defaults(func=cmd_why)

    p = sub.add_parser("export", help="emitir la trayectoria como trajectory.v1 JSON")
    p.add_argument("trajectory_id")
    p.set_defaults(func=cmd_export)

    p = sub.add_parser("doctor", help="auto-diagnóstico de invariantes")
    p.add_argument("--json", action="store_true")
    p.set_defaults(func=cmd_doctor)

    p = sub.add_parser("selftest", help="replay end-to-end de los hooks en un store desechable")
    p.add_argument("--dump", help="escribir la trayectoria resultante a este archivo")
    p.set_defaults(func=cmd_selftest)

    p = sub.add_parser("dev", help="estado de desarrollo del propio plugin")
    p.set_defaults(func=cmd_dev)

    args = parser.parse_args(argv)
    return args.func(args)
