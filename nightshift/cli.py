"""CLI de nightshift: `nightshift <subcomando>` (o `python3 -m nightshift`).

Las skills del plugin son envoltorios finos sobre estos subcomandos. La lógica vive
acá para que se pueda testear sin un harness corriendo.
"""

from __future__ import annotations

import argparse
import json
import os
import shlex
import subprocess
import sys
import tempfile
from pathlib import Path

from . import __version__, config, context, store
from .redact import SECRET_RULES, Redactor

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
        print("dream fase 1 (`consolidate`) existe: las `candidate` salieron de ahí.")
        print("La fase 2 (`verify`) es M5 y no existe, así que **nada llega a")
        print("`procedure`**: ninguna memoria inyectada está verificada.")
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

        # Una `candidate` se inyecta por su patrón, no por sus pasos: si `why` no muestra
        # el patrón, no está reconstruyendo el origen de lo que se inyectó (condición de
        # éxito 3).
        if row["abstraction_json"]:
            abstraction = json.loads(row["abstraction_json"])
            print()
            print("abstracción (dream fase 1, sin verificar):")
            print("  patrón        : %s" % abstraction.get("pattern", "—"))
            if abstraction.get("decisive_signal"):
                print("  señal decisiva: %s" % abstraction["decisive_signal"])
            for señal in abstraction.get("signals", []):
                print("  señal         : %s" % señal)
            for item in json.loads(row["valid_when_json"] or "[]"):
                print("  aplica cuando : %s (%s)" % (item.get("condition", ""),
                                                     item.get("source", "inferred")))
        if row["superseded_by"]:
            print()
            print("contradicha por %s — esta trayectoria sobrevive enlazada, no se borró."
                  % row["superseded_by"][:8])
            print("  `/nightshift:why %s` muestra la sucesora." % row["superseded_by"][:8])
        supersedidas = conn.execute(
            "SELECT id FROM trajectories WHERE superseded_by = ?", (row["id"],)).fetchall()
        if supersedidas:
            print()
            print("contradice a %d trayectoria(s) anterior(es):" % len(supersedidas))
            for item in supersedidas:
                print("  %s  `/nightshift:why %s`" % (item["id"][:8], item["id"][:8]))
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


# -------------------------------------------------------------------------- audit
def cmd_audit(args) -> int:
    """Gate de M1: afirmar sobre el store real que no se filtró nada.

    Sale 1 si encuentra algo o si hay menos de `--min-sessions` sesiones distintas. El
    reporte nombra trayectoria, paso, campo y regla; **nunca el valor** que disparó la
    regla (`audit.py`).
    """
    from . import audit as audit_mod

    if not config.config_path().is_file():
        print("nightshift no está configurado: no hay `deny_paths` contra qué auditar.",
              file=sys.stderr)
        print("Corré `nightshift init` (spec §8.1).", file=sys.stderr)
        return 1

    cfg = config.load()
    red = Redactor(deny_paths=cfg["deny_paths"], home_dir=str(Path.home()))
    conn = store.connect()
    try:
        report = audit_mod.audit_store(conn, redactor=red, home_dir=str(Path.home()))
    finally:
        conn.close()

    findings = report["findings"]
    sessions_ok = report["sessions"] >= args.min_sessions
    report["min_sessions"] = args.min_sessions
    report["sessions_ok"] = sessions_ok
    report["ok"] = sessions_ok and not findings

    if args.json:
        report["store"] = str(config.db_path())
        json.dump(report, sys.stdout, indent=2, ensure_ascii=False)
        sys.stdout.write("\n")
        return 0 if report["ok"] else 1

    print("nightshift audit · %s" % __version__)
    print("store: %s" % config.db_path())
    print()
    print("alcance:")
    print("  %-13s %d%s" % ("sesiones", report["sessions"],
                            "  (mínimo exigido: %d)" % args.min_sessions
                            if args.min_sessions else ""))
    for key, label in (("trajectories", "trayectorias"), ("steps", "pasos"),
                       ("injections", "inyecciones")):
        print("  %-13s %d" % (label, report[key]))
    print("  %-13s %d revisados contra %d deny_paths + %d reglas de secreto" % (
        "campos", report["fields_scanned"], report["deny_paths"], len(SECRET_RULES)))
    print()
    if findings:
        print("hallazgos: %d — se dice dónde y qué regla, nunca el valor:" % len(findings))
        for item in findings:
            print("  %-16s trayectoria=%s paso=%-4s campo=%s  pos=%d len=%d" % (
                item["rule"], (item["trajectory"] or "—")[:8],
                "—" if item["step"] is None else item["step"],
                item["field"], item["pos"], item["len"]))
        print()
        print("`nightshift why <trayectoria>` ubica el paso. El valor se mira en el store,")
        print("no en este reporte.")
    else:
        print("hallazgos: ninguno")
    if not sessions_ok:
        print()
        print("sesiones: %d < %d exigidas. El gate de M1 pide 5 sesiones reales capturadas;"
              % (report["sessions"], args.min_sessions))
        print("el código puede estar limpio y el gate seguir sin cerrarse por falta de uso.")
    print()
    if report["ok"]:
        verdict = "OK"
    else:
        parts = []
        if findings:
            parts.append("%d hallazgo(s)" % len(findings))
        else:
            parts.append("sin fugas")
        if not sessions_ok:
            parts.append("%d de %d sesiones" % (report["sessions"], args.min_sessions))
        verdict = ", ".join(parts)
    print("audit: %s" % verdict)
    return 0 if report["ok"] else 1


# -------------------------------------------------------------------------- dream
def _model_for(cfg, override=None, timeout=None):
    from . import dream as dream_mod

    command = shlex.split(override) if override else dream_mod.detect_command(cfg)
    if not command:
        raise dream_mod.ModelUnavailable(
            "no hay modelo local disponible. dream corre con Qwen local por `subprocess`;\n"
            "no hay fallback remoto (spec §2.2). Instalá ollama y bajá un modelo qwen,\n"
            "o fijá `model_command` en %s." % config.config_path())
    return dream_mod.LocalModel(command, timeout=timeout or cfg.get("dream_timeout_seconds", 180))


def _print_dream_report(report):
    print("modelo: %s" % report["model"])
    print("período: últimos %d día(s)" % report["lookback_days"])
    print("grupos: %d sobre %d trayectoria(s) cerrada(s)"
          % (report["groups"], report["trajectories"]))
    print()
    if report["candidates"]:
        print("candidatas (%d)%s:" % (len(report["candidates"]),
                                      " — dry-run, no se escribió nada" if report["dry_run"]
                                      else ""))
        for item in report["candidates"]:
            print("  %s  %-20s valid_when=%d" % (item["trajectory"][:8], item["task_type"],
                                                 item["valid_when"]))
            print("      %s" % item["pattern"][:150])
    else:
        print("candidatas: ninguna")
    if report["superseded"]:
        print()
        print("contradicciones (%d) — la vieja queda `superseded`, no borrada:"
              % len(report["superseded"]))
        for item in report["superseded"]:
            print("  %s  <- superseded_by %s" % (item["trajectory"][:8], item["by"][:8]))
    if report["skipped"]:
        print()
        print("grupos sin patrón común (%d) — el modelo dijo que no comparten nada:"
              % len(report["skipped"]))
        for item in report["skipped"]:
            print("  %s" % item["trajectory"][:8])
    if report["rejected"]:
        print()
        print("grupos descartados (%d) — el modelo no produjo algo persistible:"
              % len(report["rejected"]))
        for item in report["rejected"]:
            print("  %s  %s" % (item["trajectory"][:8], "; ".join(item["reasons"])[:160]))
    print()
    print("nada de esto está verificado: `verify` es M5 y no existe. Son `candidate`,")
    print("se inyectan con menos peso y marcadas como no verificadas (spec §6.3).")


def cmd_dream(args) -> int:
    """Dream fase 1. Sale 2 sin modelo local, 1 si había material y no consolidó nada."""
    from . import dream as dream_mod

    if args.selftest:
        return _dream_selftest(args)

    if not config.config_path().is_file():
        print("nightshift no está configurado. Corré `nightshift init`.", file=sys.stderr)
        return 2
    cfg = config.load()
    try:
        model = _model_for(cfg, args.model, args.timeout)
    except dream_mod.ModelUnavailable as exc:
        print("dream: %s" % exc, file=sys.stderr)
        return 2

    started = store.now()
    red = Redactor(deny_paths=cfg["deny_paths"], home_dir=str(Path.home()))
    conn = store.connect()
    try:
        report = dream_mod.consolidate(
            conn, model, cfg=cfg,
            identifiers=dream_mod.redactor_identifiers(os.getcwd()),
            lookback_days=args.lookback_days, dry_run=args.dry_run,
            log=(lambda message: print("  %s" % message, file=sys.stderr))
            if args.verbose else None)
    except dream_mod.ModelUnavailable as exc:
        # No hay modelo: es lo mismo que no haberlo detectado nunca, y se distingue de
        # "el modelo corrió y no sirvió" en el código de salida.
        _record_run(conn, args, started, 2, note=red.text(str(exc)))
        print("dream: %s" % exc, file=sys.stderr)
        return 2
    except dream_mod.DreamError as exc:
        _record_run(conn, args, started, 1, note=red.text(str(exc)))
        print("dream: %s" % exc, file=sys.stderr)
        return 1
    finally:
        conn.close()

    if args.json:
        json.dump(report, sys.stdout, indent=2, ensure_ascii=False)
        sys.stdout.write("\n")
    else:
        print("nightshift dream · consolidate (M3-a)")
        print()
        _print_dream_report(report)

    if report["candidates"]:
        code, note = 0, None
    elif report["trajectories"] == 0:
        # No había nada que consolidar. Eso no es un fallo: es una noche tranquila.
        code, note = 0, "nada que consolidar en el período"
        print("\nnada que consolidar en el período." if not args.json else "",
              file=sys.stderr)
    else:
        # Había material y no salió ninguna candidata: dream no consolidó. Lo dice.
        code, note = 1, "había material y no salió ninguna candidata"
        print("\ndream no consolidó nada de %d trayectoria(s)." % report["trajectories"],
              file=sys.stderr)

    if not args.dry_run:
        conn = store.connect()
        try:
            _record_run(conn, args, started, code, report=report, note=note)
        finally:
            conn.close()
    return code


def _record_run(conn, args, started, exit_code, report=None, note=None):
    """Deja la corrida en el store. Es lo único que `schedule status` tiene para mostrar."""
    report = report or {}
    store.record_run(conn, command="dream", backend=getattr(args, "backend", None) or "manual",
                     started_at=started, exit_code=exit_code,
                     trajectories=report.get("trajectories", 0),
                     candidates=len(report.get("candidates", [])),
                     superseded=len(report.get("superseded", [])),
                     rejected=len(report.get("rejected", [])),
                     note=(note or "")[:200] or None)


FIXTURE = [
    {"task_type": "debug_test_failure", "outcome": "user_corrected", "contradicted": True,
     "steps": [("tool_use", "run_shell", "la suite falla en el borde de decodificación"),
               ("tool_use", "edit_file", "se cambió el manejo de excepciones del lector"),
               ("observation", "observation", "el fallo persiste: la corrección no era ahí")]},
    {"task_type": "debug_test_failure", "outcome": "tests_passed", "contradicted": False,
     "steps": [("tool_failure", "run_shell",
                "UnicodeDecodeError al leer el archivo de entrada"),
               ("tool_use", "read_file", "el lector abre en modo texto sin declarar encoding"),
               ("tool_use", "edit_file", "se declara el encoding explícito al abrir"),
               ("tool_use", "run_shell", "la suite pasa entera")]},
    {"task_type": "refactor", "outcome": "tests_passed", "contradicted": False,
     "steps": [("tool_use", "search", "la misma expresión aparece en tres módulos"),
               ("tool_use", "edit_file", "se extrae a una función común"),
               ("tool_use", "run_shell", "la suite pasa entera")]},
]


def _seed_fixture(conn, repo_name):
    """Set fixture de trayectorias cerradas. El nombre del repo va adentro a propósito.

    Si el modelo lo copia al abstraer, el gate tiene que verlo: `abstraction` es lo único
    que puede cruzar de repo A a repo B (spec §4.2), así que un nombre de repo ahí es
    una fuga, no un detalle.
    """
    ids = []
    for i, item in enumerate(FIXTURE):
        tid = store.open_trajectory(conn, session_id="fixture-%d" % i,
                                    repo_fingerprint="f" * 64, task_type=item["task_type"],
                                    base_commit="abc1234",
                                    redaction={"redactor_version": "0.1.0"})
        for kind, tool, summary in item["steps"]:
            store.append_step(conn, tid, kind=kind, tool=tool,
                              result_summary="en %s: %s" % (repo_name, summary),
                              decisive=(kind == "tool_failure"))
        if item["contradicted"]:
            store.mark_last_contradicted(conn, tid)
        store.close_trajectory(conn, tid, result=item["outcome"])
        ids.append(tid)
    return ids


def _dream_selftest(args) -> int:
    """Gate de M3-a. Corre el modelo local de verdad sobre un set fixture desechable."""
    from . import dream as dream_mod

    repo_name = "fixturerepo"
    failures = []
    with tempfile.TemporaryDirectory(prefix="nightshift-dream-") as tmp:
        previous = os.environ.get("NIGHTSHIFT_HOME")
        os.environ["NIGHTSHIFT_HOME"] = tmp
        try:
            config.init(force=True)
            cfg = config.load()
            try:
                model = _model_for(cfg, args.model, args.timeout)
            except dream_mod.ModelUnavailable as exc:
                print("dream --selftest: %s" % exc, file=sys.stderr)
                return 2
            print("modelo: %s" % model.name)

            conn = store.connect()
            try:
                sembradas = _seed_fixture(conn, repo_name)
                try:
                    report = dream_mod.consolidate(
                        conn, model, cfg=cfg, identifiers=[repo_name], lookback_days=3650,
                        log=lambda message: print("  %s" % message))
                except dream_mod.DreamError as exc:
                    print("  FALLA  el modelo local no entregó: %s" % exc)
                    print("dream --selftest: 1 fallo(s)")
                    return 1

                if not report["candidates"]:
                    failures.append("ninguna trayectoria llegó a `candidate`")
                for item in report["candidates"]:
                    doc = store.export_trajectory(conn, item["trajectory"])
                    pattern = (doc.get("abstraction") or {}).get("pattern", "")
                    if doc["status"] != "candidate":
                        failures.append("%s quedó en %s" % (item["trajectory"][:8],
                                                            doc["status"]))
                    if not pattern:
                        failures.append("%s es candidate sin `abstraction.pattern`"
                                        % item["trajectory"][:8])
                    # Se mira la abstracción, no la trayectoria entera: los pasos del
                    # fixture nombran el repo a propósito. Lo que no puede nombrarlo es lo
                    # único que cruza de repo A a repo B (spec §4.2).
                    portable = json.dumps({"abstraction": doc.get("abstraction"),
                                           "valid_when": doc.get("valid_when")},
                                          ensure_ascii=False).lower()
                    if repo_name in portable:
                        failures.append("FUGA: el nombre del repo fixture sobrevivió en la"
                                        " abstracción de %s" % item["trajectory"][:8])
                    from .audit import ABSTRACTION_PATH_RE
                    if ABSTRACTION_PATH_RE.search(pattern):
                        failures.append("%s tiene una ruta en `abstraction.pattern`"
                                        % item["trajectory"][:8])
                    if doc["verified"] is not None:
                        failures.append("%s dice estar verificada y `verify` no existe"
                                        % item["trajectory"][:8])

                supers = conn.execute(
                    "SELECT * FROM trajectories WHERE status = 'superseded'").fetchall()
                for row in supers:
                    if not row["superseded_by"]:
                        failures.append("%s es `superseded` sin enlace" % row["id"][:8])
                vivas = conn.execute("SELECT COUNT(*) c FROM trajectories").fetchone()["c"]
                if vivas != len(sembradas):
                    failures.append("dream borró trayectorias: quedaron %d de %d"
                                    % (vivas, len(sembradas)))
                print()
                _print_dream_report(report)
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
        print("dream --selftest: %d fallo(s)" % len(failures))
        return 1
    print("dream --selftest: OK — ≥1 candidate, sin fuga del repo fixture, sin rutas en")
    print("el patrón, contradicción enlazada y ninguna trayectoria borrada.")
    return 0


# ----------------------------------------------------------------------- schedule
def _schedule_state(cfg, requested=None):
    from . import schedule as sched

    chosen = sched.resolve(requested, cfg)
    instalados = []
    for name in sched.BACKENDS:
        other = sched.backend(name, cfg)
        if other.installed():
            instalados.append(other)
    return chosen, instalados


def cmd_schedule(args) -> int:
    from . import schedule as sched

    if not config.config_path().is_file():
        print("nightshift no está configurado. Corré `nightshift init`.", file=sys.stderr)
        return 2
    cfg = config.load()
    try:
        chosen, instalados = _schedule_state(cfg, args.backend)
    except ValueError as exc:
        print("schedule: %s" % exc, file=sys.stderr)
        return 2

    if args.action == "install":
        result = chosen.install(dry_run=args.dry_run, activate=not args.no_activate)
        if args.dry_run:
            print("backend: %s (dry-run, no se escribió nada)" % chosen.name)
            print("unidad que se escribiría en %s:" % result["path"])
            print()
            print(result["unit"])
            if "service" in result:
                print(result["service"])
            return 0
        print("backend   : %s" % chosen.name)
        print("unidad    : %s" % result["path"])
        print("corrida   : %s · %s" % (chosen.describe(), " ".join(chosen.command())))
        print("activada  : %s (%s)" % ("sí" if result["activated"] else "no",
                                       result.get("detail", "")))
        if chosen.name == "loop":
            print()
            print("`loop` no instala nada en el sistema: corré `nightshift schedule loop`")
            print("en primer plano, o dejalo en un tmux. Es el backend de desarrollo.")
        return 0 if (result["activated"] or args.no_activate or chosen.name == "loop") else 1

    if args.action == "uninstall":
        borrado = False
        for other in instalados or [chosen]:
            result = other.uninstall()
            borrado = borrado or result["removed"]
            print("%-9s %s (%s)" % (other.name,
                                    "desinstalado" if result["removed"] else "no estaba",
                                    result.get("detail", "")))
        return 0 if borrado else 1

    if args.action == "loop":
        return _schedule_loop(args, cfg, chosen)

    return _schedule_status(args, cfg, chosen, instalados, sched)


def _schedule_status(args, cfg, chosen, instalados, sched) -> int:
    conn = store.connect()
    try:
        runs = store.recent_runs(conn, args.limit)
    finally:
        conn.close()

    if args.json:
        json.dump({
            "backend_elegido": chosen.name,
            "instalados": [{"backend": b.name, "unit": str(b.unit_path)} for b in instalados],
            "entorno": sched.environment(),
            "corridas": [dict(row) for row in runs],
        }, sys.stdout, indent=2, ensure_ascii=False)
        sys.stdout.write("\n")
        return 0 if instalados else 1

    print("nightshift schedule · %s" % __version__)
    entorno = sched.environment()
    print("plataforma : %s%s" % (entorno["platform"],
                                 " · caffeinate" if entorno["caffeinate"] else ""))
    print("backend    : %s%s" % (chosen.name,
                                 " (autodetectado)" if cfg.get("scheduler_backend", "auto")
                                 == "auto" else " (fijado en la config)"))
    print("corrida    : %s" % chosen.describe())
    print("comando    : %s" % " ".join(chosen.command()))
    if instalados:
        for item in instalados:
            print("instalado  : %s → %s" % (item.name, item.unit_path))
    else:
        print("instalado  : no. `nightshift schedule install` lo deja programado.")
    print()
    if runs:
        print("últimas corridas:")
        for row in runs:
            veredicto = {0: "ok", 1: "no consolidó", 2: "sin modelo local"}.get(
                row["exit_code"], "exit=%s" % row["exit_code"])
            print("  %s  %-8s %-9s %-16s cand=%d sup=%d desc=%d  %s" % (
                row["started_at"], row["command"], row["backend"] or "—", veredicto,
                row["candidates"] or 0, row["superseded"] or 0, row["rejected"] or 0,
                (row["note"] or "")[:60]))
    else:
        print("últimas corridas: ninguna todavía.")
        print("Un scheduler sin corridas registradas es una promesa, no un hecho.")
    print()
    print("el gate de M3 no es este comando: son tres noches seguidas sin intervención.")
    print("Esto las hace verificables.")
    return 0 if instalados else 1


def _schedule_loop(args, cfg, chosen) -> int:
    """Backend `loop`: dream cada N minutos, en primer plano. Ctrl-C para salir."""
    import time

    intervalo = (args.interval_minutes or int(cfg.get("loop_interval_minutes", 360))) * 60
    print("nightshift schedule loop · cada %d minuto(s) · Ctrl-C para salir"
          % (intervalo // 60))
    while True:
        print("\n--- %s: dream" % store.now())
        code = main(["dream", "--backend", "loop"])
        print("--- dream salió %d" % code)
        if args.once:
            return code
        try:
            time.sleep(intervalo)
        except KeyboardInterrupt:
            print("\nloop interrumpido.")
            return 0


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

    # El gate de M1 hecho invariante de runtime: el store persistido no puede tener
    # fugas. `nightshift audit` es el reporte; acá es una aserción más del doctor.
    try:
        from . import audit as audit_mod

        conn = store.connect()
        try:
            reporte = audit_mod.audit_store(
                conn, redactor=Redactor(deny_paths=cfg["deny_paths"],
                                        home_dir=str(Path.home())),
                home_dir=str(Path.home()))
        finally:
            conn.close()
        hallazgos = reporte["findings"]
        checks.append(_check(
            "store sin fugas (audit)", not hallazgos,
            "%d campo(s) revisados" % reporte["fields_scanned"] if not hallazgos
            else "%d hallazgo(s): corré `nightshift audit`" % len(hallazgos)))
    except Exception as exc:
        checks.append(_check("store sin fugas (audit)", False, str(exc)))

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
    print("milestone actual: M3-a — dream `consolidate`")
    print("  hecho     : captura, redactor, store, retrieval, /why, audit, dream fase 1")
    print("  falta     : M3-b scheduler, M4 benchmark (go/no-go), M5 verify")
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

    p = sub.add_parser("audit", help="auditar el store persistido: fugas y cobertura (gate de M1)")
    p.add_argument("--min-sessions", type=int, default=0,
                   help="exigir al menos N sesiones distintas capturadas (el gate de M1 usa 5)")
    p.add_argument("--json", action="store_true")
    p.set_defaults(func=cmd_audit)

    p = sub.add_parser("dream", help="consolidar trayectorias cerradas con el modelo local (M3-a)")
    p.add_argument("--lookback-days", type=int, default=None)
    p.add_argument("--model", help="comando del modelo local (por defecto, autodetección)")
    p.add_argument("--timeout", type=int, default=None, help="segundos por llamada al modelo")
    p.add_argument("--dry-run", action="store_true", help="no escribir: mostrar qué haría")
    p.add_argument("--verbose", action="store_true")
    p.add_argument("--backend", default=None,
                   help="quién disparó esta corrida: queda en el registro de `schedule status`")
    p.add_argument("--selftest", action="store_true",
                   help="gate de M3-a: correr sobre un set fixture en un store desechable")
    p.add_argument("--json", action="store_true")
    p.set_defaults(func=cmd_dream)

    p = sub.add_parser("schedule", help="programar la corrida nocturna (M3-b)")
    p.add_argument("action", nargs="?", default="status",
                   choices=("status", "install", "uninstall", "loop"))
    p.add_argument("--backend", default=None, choices=("auto", "launchd", "systemd", "loop"))
    p.add_argument("--dry-run", action="store_true",
                   help="mostrar la unidad sin escribirla")
    p.add_argument("--no-activate", action="store_true",
                   help="escribir la unidad sin cargarla en el gestor del sistema")
    p.add_argument("--interval-minutes", type=int, default=None, help="sólo para `loop`")
    p.add_argument("--once", action="store_true", help="sólo para `loop`: una vuelta y salir")
    p.add_argument("--limit", type=int, default=10)
    p.add_argument("--json", action="store_true")
    p.set_defaults(func=cmd_schedule)

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
