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
import time
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


def _format_size(n: int) -> str:
    value = float(n)
    for unit in ("B", "KB", "MB", "GB"):
        if value < 1024 or unit == "GB":
            return "%.0f %s" % (value, unit) if unit == "B" else "%.1f %s" % (value, unit)
        value /= 1024
    return "%.1f GB" % value


# ------------------------------------------------------------------------- status
def cmd_status(args) -> int:
    if not config.config_path().is_file():
        print("nightshift no está configurado. Corré `nightshift init`.")
        print("Sin `deny_paths` resuelto no se captura nada (spec §8.1).")
        return 0
    cfg = config.load()
    conn = store.connect()
    try:
        c = store.counts(conn)
        print("nightshift %s · M3: captura, retrieval y dream fase 1" % __version__)
        print("store: %s (%s en disco)" % (config.db_path(), _format_size(store.store_size_bytes())))
        print()
        print("trayectorias:")
        for status in ("open", "closed", "candidate", "procedure", "superseded", "discarded"):
            print("  %-11s %d" % (status, c[status]))
        print("  %-11s %d" % ("pasos", c["steps"]))
        print("  %-11s %d" % ("inyecciones", c["injections"]))
        calidad = store.capture_quality(conn)
        if calidad["tool_steps"]:
            print()
            print("calidad de la captura (últimas %d trayectorias):" % calidad["trajectories"])
            print("  %-11s %d" % ("pasos tool", calidad["tool_steps"]))
            print("  %-11s %d (%.0f%%)" % ("sin contenido", calidad["hollow"],
                                             100 * calidad["hollow_ratio"]))
            print("  %-11s %d (%.0f%%)" % ("decisivos", calidad["decisive"],
                                           100 * calidad["decisive_ratio"]))
            print("  %-11s %d (caen a `other`)" % ("sin mapear", calidad["unmapped"]))
            ultima = calidad["latest"]
            if ultima:
                print("  %-11s %s" % ("última", "captura con contenido"
                                      if ultima["healthy"]
                                      else "SIN contenido: la captura está rota AHORA"))
            if calidad["broken"]:
                print("  %d trayectoria(s) con pasos y ninguno con contenido: %s"
                      % (len(calidad["broken"]),
                         ", ".join(t[:8] for t in calidad["broken"][:4])))
                print("  (las anteriores al 2026-08-26 son cascarón por el bug de los")
                print("   campos del payload; ver LATER.md)")
        print()
        from . import dream as dream_mod

        backend = cfg.get("model_backend", "claude-code")
        comando = dream_mod.detect_command(cfg)
        print("consolidación: %s%s" % (
            backend if comando else "%s — NO disponible" % backend,
            "  · lo redactado sale de la máquina (ADR-003)"
            if comando and backend == "claude-code" else
            "  · nada sale de la máquina" if comando else ""))
        print()
        print("dream fase 1 (`consolidate`) existe: las `candidate` salieron de ahí.")
        print("La fase 2 (`verify`) es M5 y no existe, así que **nada llega a")
        print("`procedure`**: ninguna memoria inyectada está verificada.")
        rows = conn.execute(
            "SELECT * FROM trajectories ORDER BY created_at DESC, rowid DESC LIMIT ?",
            (args.limit,)).fetchall()
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
            print("  consolidada con: %s" % (row["consolidation_model"] or "—"))
            print("  consolidar usó: %s" % (
                "USD %.4f a precio de lista" % row["consolidation_cost_usd"]
                if row["consolidation_cost_usd"] is not None
                else "no reportado por el backend"))
            if "ideation" in row.keys() and row["ideation"]:
                print("  mecanismo     : %s" % row["ideation"])
            print("  patrón        : %s" % abstraction.get("pattern", "—"))
            if abstraction.get("decisive_signal"):
                print("  señal decisiva: %s" % abstraction["decisive_signal"])
            proyectadas = []
            if ("projected_signals_json" in row.keys()
                    and row["projected_signals_json"]):
                try:
                    proyectadas = json.loads(row["projected_signals_json"]) or []
                except ValueError:
                    proyectadas = []
            for señal in abstraction.get("signals", []):
                print("  señal         : %s" % señal)
            # Lo proyectado va después de lo observado y dice que lo es. `why` existe
            # para reconstruir de dónde salió una inyección: una conjetura listada como
            # señal sería una reconstrucción falsa.
            for señal in proyectadas:
                print("  anticipada    : %s (conjetura: nadie la observó)" % señal)
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
    # El mínimo se mide contra las sesiones que **capturaron contenido**: el gate de M1
    # pide sesiones reales sin fuga, y una sesión hueca no prueba ausencia de fuga.
    sessions_ok = report["sessions_with_content"] >= args.min_sessions
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
    print("  %-13s %d" % ("sesiones", report["sessions"]))
    huecas = report["sessions"] - report["sessions_with_content"]
    print("  %-13s %d%s%s" % (
        "con contenido", report["sessions_with_content"],
        "  (mínimo exigido: %d)" % args.min_sessions if args.min_sessions else "",
        "  · %d hueca(s) no cuentan" % huecas if huecas else ""))
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
        print("sesiones con contenido: %d < %d exigidas. El gate de M1 pide sesiones"
              % (report["sessions_with_content"], args.min_sessions))
        print("reales capturadas, y una sesión cuyos pasos están vacíos no prueba ausencia")
        print("de fuga: no se puede filtrar lo que nunca se guardó.")
        if huecas:
            print("Hay %d sesión(es) hueca(s) en el store que no cuentan (ver LATER.md)."
                  % huecas)
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
            parts.append("%d de %d sesiones con contenido"
                         % (report["sessions_with_content"], args.min_sessions))
        verdict = ", ".join(parts)
    print("audit: %s" % verdict)
    return 0 if report["ok"] else 1


# -------------------------------------------------------------------------- dream
def _model_for(cfg, override=None, timeout=None):
    from . import dream as dream_mod

    command = shlex.split(override) if override else dream_mod.detect_command(cfg)
    if not command:
        backend = cfg.get("model_backend", "claude-code")
        raise dream_mod.ModelUnavailable(
            "no hay con qué consolidar: el backend `%s` no tiene su ejecutable.\n"
            "Por defecto dream consolida con Claude Code —el agente que ya está\n"
            "instalado— invocándolo por `subprocess` (ADR-003). Con\n"
            "`model_backend: \"local\"` usa Qwen por ollama, y `model_command` acepta\n"
            "cualquier ejecutable que lea un prompt por stdin. Config: %s"
            % (backend, config.config_path()))
    return dream_mod.LocalModel(command, timeout=timeout or cfg.get("dream_timeout_seconds", 180))


def _print_dream_report(report):
    print("modelo: %s" % report["model"])
    print("período: últimos %d día(s)" % report["lookback_days"])
    if report.get("input_tokens") or report.get("output_tokens"):
        linea = "uso: %s tokens de entrada · %s de salida" % (
            "{:,}".format(report.get("input_tokens") or 0),
            "{:,}".format(report.get("output_tokens") or 0))
        if report.get("cost_usd"):
            # A precio de lista. Con una suscripción de Claude Code no se factura esto.
            linea += " (USD %.4f a precio de lista)" % report["cost_usd"]
        print(linea)
    elif report.get("cost_usd"):
        print("uso: USD %.4f a precio de lista" % report["cost_usd"])
    print("grupos: %d sobre %d trayectoria(s) cerrada(s)"
          % (report["groups"], report["trajectories"]))
    if report.get("groups_skipped_by_limit"):
        print("       %d grupo(s) más sin consolidar por --max-groups: quedan para la"
              " próxima corrida" % report["groups_skipped_by_limit"])
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
            lookback_days=args.lookback_days, max_groups=args.max_groups, dry_run=args.dry_run,
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
    elif report["rejected"]:
        # El modelo produjo algo y no se pudo persistir: eso sí es que dream no consolidó.
        code, note = 1, "el modelo no produjo nada persistible en %d grupo(s)" % len(
            report["rejected"])
        print("\ndream no consolidó: %d grupo(s) descartado(s)." % len(report["rejected"]),
              file=sys.stderr)
    elif report["skipped"]:
        # "Estas trayectorias no comparten patrón" es una respuesta legítima del modelo,
        # no un fallo. Salir 1 acá haría que una noche normal figure como corrida fallida
        # en `schedule status`, y el gate de M3 —tres noches sin intervención— dejaría de
        # poder distinguir una noche tranquila de una que hay que ir a mirar.
        code, note = 0, "sin patrón común en %d grupo(s): noche tranquila" % len(
            report["skipped"])
        print("\nel modelo no encontró patrón común en %d grupo(s)." % len(report["skipped"]),
              file=sys.stderr)
    else:
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
                     cost_usd=report.get("cost_usd"),
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


# ----------------------------------------------------------------------- simulate
def cmd_simulate(args) -> int:
    """Ensayo end-to-end sobre un store desechable.

    **No cierra el gate de M1 ni el de M3.** Ésos piden sesiones reales y noches reales;
    esto ejercita la máquina, que es otra cosa. La distinción está en `simulate.py` y se
    repite en la salida a propósito: un ensayo que se reporta como gate es evidencia
    fabricada.
    """
    from . import simulate as sim

    print("nightshift simulate · ensayo end-to-end · %s" % __version__)
    print("store: temporal — el store real no se toca")
    print()
    reporte = sim.run(cwd=os.getcwd(), con_modelo=not args.no_model, noches=args.nights,
                      log=print)

    print()
    print("resultado del ensayo:")
    a = reporte["auditoria"]
    print("  captura      : %d sesiones distintas, %d trayectorias, %d pasos"
          % (a["sessions"], a["trajectories"], a["steps"]))
    print("  deny_paths   : %d intento(s) bloqueado(s), 0 capturados"
          % reporte.get("deny_path_hits", 0))
    print("  auditoría    : %d campos revisados, %d hallazgo(s)"
          % (a["fields_scanned"], len(a["findings"])))
    print("  huérfana     : quedó `%s`" % reporte.get("huerfana", "?"))
    inyecciones = reporte.get("inyecciones_sesion_nueva", [])
    print("  retrieval    : %d inyección(es) en la sesión nueva · %s"
          % (len(inyecciones), ", ".join(sorted({i["reason"] for i in inyecciones})) or "—"))
    if "dream" in reporte:
        d = reporte["dream"]
        print("  dream        : %d candidata(s), %d contradicción(es) enlazada(s), "
              "%d descartada(s)" % (len(d["candidates"]), len(d["superseded"]),
                                    len(d["rejected"])))
        print("                 estados: %s" % ", ".join(
            "%s=%s" % (k, v) for k, v in sorted(d["estados"].items())))
    corridas = reporte.get("corridas", [])
    print("  scheduler    : %d corrida(s) registrada(s) · %s"
          % (len(corridas), ", ".join("exit=%s" % r["exit_code"] for r in corridas)))
    final = reporte.get("auditoria_final", {})
    print("  auditoría 2  : %d campos, %d hallazgo(s), %d corrida(s) en el store"
          % (final.get("fields_scanned", 0), len(final.get("findings", [])),
             final.get("runs", 0)))

    if args.dump:
        Path(args.dump).write_text(json.dumps(reporte, indent=2, ensure_ascii=False) + "\n",
                                   encoding="utf-8")
        print("  dump         : %s" % args.dump)

    print()
    fallas = reporte["fallas"]
    if fallas:
        for item in fallas:
            print("  FALLA  %s" % item)
        print("simulate: %d fallo(s)" % len(fallas))
        return 1
    print("simulate: OK — la máquina completa funciona de punta a punta.")
    print()
    print("Lo que esto NO es: el gate de M1 pide 5 sesiones **reales** y el de M3, tres")
    print("noches **reales** sin intervención. Un ensayo no las reemplaza — no hay")
    print("suspensión, ni batería, ni un launchd que se olvidó de disparar, que es")
    print("justamente lo que esos gates miden. Ese conteo sigue donde estaba.")
    return 0


# -------------------------------------------------------------------------- bench
PREREG_PATH = PLUGIN_ROOT / "bench" / "PREREG.md"
SELFTEST_FIXTURE = PLUGIN_ROOT / "bench" / "fixtures" / "selftest"


def _bench_dir():
    return config.guard_path(config.home() / "bench")


def _print_readiness(prereg, estado):
    print("pre-registro : %s" % prereg["path"])
    print("estado       : %s" % prereg["estado"])
    print("umbrales     : %s" % ", ".join(
        "%s=%s" % (f, (bench_mod.primary_threshold(prereg, f) or {}).get("raw", "—"))
        for f in bench_mod.FAMILIES))
    print()
    if estado["ready"]:
        print("listo para correr: sí")
        return
    print("listo para correr: NO")
    for item in estado["blockers"]:
        print("  - %s" % item)
    if prereg["todos"]:
        print()
        print("TODO pendientes, por sección:")
        seccion = None
        for item in prereg["todos"]:
            if item["section"] != seccion:
                seccion = item["section"]
                print("  §%s" % seccion)
            print("    línea %-4d %s" % (item["line"], item["text"]))


def cmd_bench(args) -> int:
    """Runner del benchmark de M4. **No fija umbrales: los lee.**"""
    global bench_mod
    from . import bench as bench_mod

    if args.action == "selftest":
        return _bench_selftest(args)

    prereg = bench_mod.read_prereg(args.prereg or PREREG_PATH)
    estado = bench_mod.readiness(prereg)

    if args.action == "check":
        if args.json:
            json.dump({"prereg": {k: prereg[k] for k in ("path", "estado", "frozen", "todos")},
                       "readiness": estado}, sys.stdout, indent=2, ensure_ascii=False)
            sys.stdout.write("\n")
            return 0 if estado["ready"] else 1
        print("nightshift bench check · %s" % __version__)
        print()
        _print_readiness(prereg, estado)
        print()
        print("Claude Code lee este archivo: no propone, no completa ni ajusta umbrales.")
        print("Todo TODO(Matias) lo resuelve una persona (PREREG §regla 3).")
        return 0 if estado["ready"] else 1

    if args.action == "fixtures":
        # Los fixtures sintéticos del selftest quedan fuera a propósito: no tienen fix de
        # referencia porque su "agente" siempre resuelve. Los valida `bench selftest`.
        rutas = ([Path(args.fixture)] if args.fixture else
                 sorted(ruta for ruta in
                        (PLUGIN_ROOT / "bench" / "fixtures").glob("*/fixture*.json")
                        if ruta.parent.name != "selftest"))
        if not rutas:
            print("no encontré ningún fixture", file=sys.stderr)
            return 2
        fallas = 0
        for ruta in rutas:
            try:
                fixture = bench_mod.load_fixture(ruta)
            except bench_mod.FixtureError as exc:
                print("  %s: %s" % (ruta, exc), file=sys.stderr)
                fallas += 1
                continue
            print("%s · familia %s · %d tarea(s)"
                  % (fixture["name"], fixture["family"], len(fixture["tasks"])))
            reporte = bench_mod.check_fixture(fixture, timeout=args.timeout, log=print)
            if not reporte["ok"]:
                fallas += 1
            print()
        if fallas:
            print("bench fixtures: %d fixture(s) con problemas" % fallas)
            print("Una tarea que ya pasa, o que no se puede resolver, no mide nada.")
            return 1
        print("bench fixtures: OK — cada tarea falla antes y la resuelve su fix de "
              "referencia.")
        return 0

    if args.action == "plan":
        try:
            rutas = ([Path(args.fixture)] if args.fixture else
                     sorted(ruta for ruta in
                            (PLUGIN_ROOT / "bench" / "fixtures").glob("*/fixture*.json")
                            if ruta.parent.name != "selftest"))
            planes = []
            for ruta in rutas:
                uno = bench_mod.load_fixture(ruta)
                planes.append((uno, bench_mod.matrix(uno, rows=tuple(args.rows.split(",")),
                                                     repeats=args.repeats, seed=args.seed)))
            fixture, celdas = planes[0]
        except (bench_mod.FixtureError, ValueError, IndexError) as exc:
            print("bench plan: %s" % exc, file=sys.stderr)
            return 2

        if args.json:
            total = sum(len(c) for _, c in planes)
            json.dump({
                "fixtures": [{"name": f["name"], "family": f["family"],
                              "tasks": len(f["tasks"]),
                              "learning_tasks": f["learning_tasks"],
                              "cells": len(c)} for f, c in planes],
                "rows": args.rows.split(","), "repeats": args.repeats, "seed": args.seed,
                "cells_total": total,
                # Cada celda es una sesión real del agente: el tamaño de la grilla es el
                # tamaño de la factura, y conviene saberlo antes y no después.
                "note": "cada celda es una sesión completa del agente",
                "ready": estado["ready"], "blockers": estado["blockers"],
            }, sys.stdout, indent=2, ensure_ascii=False)
            sys.stdout.write("\n")
            return 0
        print("fixture   : %s (familia %s, %d tarea(s), %d de aprendizaje)"
              % (fixture["name"], fixture["family"], len(fixture["tasks"]),
                 fixture["learning_tasks"]))
        print("celdas    : %d = %s filas × %d corridas × %d tareas"
              % (len(celdas), args.rows, args.repeats, len(fixture["tasks"])))
        # El presupuesto de esta corrida es tiempo de pared, así que el plan lo dice
        # antes de arrancar y con datos medidos, no estimados.
        historicos = bench_mod.historical_seconds(_bench_dir())
        if historicos:
            historicos.sort()
            mediana = historicos[len(historicos) // 2]
            p90 = historicos[min(len(historicos) - 1, int(len(historicos) * 0.9))]
            print("tiempo    : ~%.1f h (mediana %.0f s/celda sobre %d celda(s) ya "
                  "corridas)" % (len(celdas) * mediana / 3600, mediana, len(historicos)))
            print("            ~%.1f h en el peor caso (p90 %.0f s/celda)"
                  % (len(celdas) * p90 / 3600, p90))
        else:
            print("tiempo    : sin corridas previas para estimarlo. `bench rehearse` "
                  "sobre una")
            print("            fila lo calibra sin desellar nada.")
        print("orden     : fijo por seed=%s, idéntico en todas las filas (PREREG §5)"
              % args.seed)
        print()
        for celda in celdas[:args.limit]:
            print("  %-3s corrida %d  %-6s %-9s %s" % (celda["row"], celda["repeat"],
                                                       celda["task"], celda["phase"],
                                                       celda["family"]))
        if len(celdas) > args.limit:
            print("  … y %d celda(s) más (--limit)" % (len(celdas) - args.limit))
        print()
        if not estado["ready"]:
            print("planificar no es correr: `bench run` va a negarse hasta que el")
            print("pre-registro esté congelado. `nightshift bench check` dice qué falta.")
        return 0

    if args.action == "rehearse":
        # Un ensayo **no** es la corrida: no exige pre-registro congelado, y por eso no
        # puede mostrar resultados. Sirve para descubrir que una celda se cuelga o que
        # 102 sesiones cuestan más de lo que se creía, sin que quien fija los umbrales
        # vea el efecto antes de fijarlos (PREREG §5).
        return _bench_run(args, prereg, estado, sealed=True)

    if args.action == "run":
        if not estado["ready"] and not args.prereg:
            print("bench run: el pre-registro no está listo. No se corre nada.",
                  file=sys.stderr)
            for item in estado["blockers"]:
                print("  - %s" % item, file=sys.stderr)
            print(file=sys.stderr)
            print("Un umbral que se ajusta después de ver el resultado no es un umbral.",
                  file=sys.stderr)
            return 3
        return _bench_run(args, prereg, estado)

    if args.action == "report":
        return _bench_report(args, prereg)

    print("acción desconocida: %s" % args.action, file=sys.stderr)
    return 2


def _bench_run(args, prereg, estado, *, quiet=False, silent_report=False,
               sealed=False) -> int:
    if not args.agent:
        print("bench run: falta `--agent`, el comando que corre el agente en cada tarea.",
              file=sys.stderr)
        return 2
    try:
        fixture = bench_mod.load_fixture(args.fixture)
        celdas = bench_mod.matrix(fixture, rows=tuple(args.rows.split(",")),
                                  repeats=args.repeats, seed=args.seed)
    except (bench_mod.FixtureError, ValueError) as exc:
        print("bench run: %s" % exc, file=sys.stderr)
        return 2

    # El id lleva segundos, y dos corridas en el mismo segundo son perfectamente
    # posibles (tres familias seguidas, por ejemplo). Sobreescribir una corrida es
    # perderla del reporte, y PREREG §4 pide publicarlas todas.
    base = time.strftime("%Y%m%dT%H%M%SZ", time.gmtime())
    run_id, sufijo = base, 1
    while (_bench_dir() / run_id).exists():
        sufijo += 1
        run_id = "%s-%d" % (base, sufijo)
    destino = _bench_dir() / run_id
    destino.mkdir(parents=True, exist_ok=True)
    (destino / "meta.json").write_text(json.dumps({
        "run_id": run_id, "fixture": fixture["path"], "family": fixture["family"],
        "rows": args.rows, "repeats": args.repeats, "seed": args.seed,
        "agent": args.agent, "prereg": prereg["path"], "prereg_estado": prereg["estado"],
        "prereg_frozen": prereg["frozen"], "nightshift": __version__,
        # Queda escrito en el registro: un ensayo no se puede confundir con la corrida.
        "rehearsal": bool(sealed),
        "budget_minutes": getattr(args, "budget_minutes", None),
    }, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

    agente = shlex.split(args.agent)
    registros = []
    # El presupuesto es tiempo de pared, no dinero: la pregunta que decide si M4 se puede
    # correr es si entra en una ventana sin nadie mirando. Y se corta **al terminar una
    # repetición**, porque la matriz va repetición → fila: cortar ahí deja las dos filas
    # con el mismo n. Cortar en el medio deja S0 más larga que S1 y eso no es un
    # resultado parcial, es un resultado torcido.
    presupuesto = getattr(args, "budget_minutes", None)
    limite_s = presupuesto * 60 if presupuesto else None
    arranque = time.monotonic()
    cortada_por_presupuesto = False
    ultima_repeticion = None
    with (destino / "results.jsonl").open("w", encoding="utf-8") as handle:
        for i, celda in enumerate(celdas, start=1):
            entorno = dict(os.environ)
            entorno["NIGHTSHIFT_BENCH_TASK"] = celda["task"]
            entorno["NIGHTSHIFT_BENCH_ROW"] = celda["row"]
            # Un directorio de trabajo por **(fila, repetición)**, con el contenido
            # reseteado antes de cada tarea. Las dos mitades importan y por motivos
            # distintos:
            #
            # - **El contenido se resetea** o la segunda tarea encuentra el fix de la
            #   primera ya hecho y el gate sale 0 sin que el agente toque nada.
            # - **La ruta se mantiene** porque las dos memorias que se comparan keyean por
            #   ruta: Auto Memory por ruta de proyecto y nightshift por fingerprint del
            #   repo, que sin remote sale de la ruta. Con una ruta nueva por tarea,
            #   ninguna de las dos acumula nada y la fase de aprendizaje no existe.
            #
            # Con rutas distintas por tarea y el store de nightshift compartido, S1
            # acumulaba memoria y S0 no: el benchmark le habría dado ventaja a nightshift
            # por construcción. Un experimento que favorece a lo que mide no mide.
            etiqueta = "%s-c%d" % (celda["row"], celda["repeat"])
            trabajo = bench_mod.prepare_workdir(fixture, destino / "trabajo" / etiqueta)
            entorno["NIGHTSHIFT_BENCH_WORKDIR"] = trabajo
            entorno["NIGHTSHIFT_ROOT"] = str(PLUGIN_ROOT)

            memoria = destino / "memoria" / etiqueta
            memoria.mkdir(parents=True, exist_ok=True)
            entorno["NIGHTSHIFT_BENCH_STORE"] = str(memoria)
            registro = bench_mod.run_cell(
                celda, fixture, agent_command=agente, timeout=args.timeout, env=entorno,
                cwd=trabajo,
                placeholders={"{agentes}": str(PLUGIN_ROOT / "bench" / "agentes"),
                              "{root}": str(PLUGIN_ROOT)})
            registros.append(registro)
            handle.write(json.dumps(registro, ensure_ascii=False) + "\n")
            handle.flush()
            if not quiet:
                # En un ensayo la línea de progreso **no dice si resolvió**: mirar eso
                # celda por celda es exactamente la inspección intermedia que PREREG §5
                # prohíbe, y sellar el reporte final no serviría de nada si el progreso
                # lo va contando.
                estado_celda = ("ok" if registro.get("agent_exit") == 0 else "falló") \
                    if sealed else "resuelto=%s" % registro.get("resolved")
                print("  [%3d/%3d] %-3s c%d %-6s %-8s %s" % (
                    i, len(celdas), celda["row"], celda["repeat"], celda["task"],
                    celda["phase"], estado_celda))

            if limite_s is None:
                continue
            transcurrido = time.monotonic() - arranque
            siguiente = celdas[i]["repeat"] if i < len(celdas) else None
            if siguiente == celda["repeat"]:
                continue                        # todavía estamos dentro de la repetición
            ultima_repeticion = celda["repeat"]
            proyectado = bench_mod.projection(registros, len(celdas))
            if transcurrido + (proyectado or 0) / len(celdas) * (
                    len(celdas) - i) > limite_s and siguiente is not None:
                cortada_por_presupuesto = True
                if not quiet:
                    print()
                    print("  presupuesto: %g min. Van %.1f min y faltan %d celda(s):"
                          % (presupuesto, transcurrido / 60, len(celdas) - i))
                    print("  se corta acá, con %d repetición(es) completas en todas las"
                          % ultima_repeticion)
                    print("  filas. Un corte en el medio de una repetición dejaría los")
                    print("  brazos con distinto n.")
                break

    integridad = bench_mod.completeness(
        registros, rows=tuple(args.rows.split(",")), repeats=args.repeats)
    meta = json.loads((destino / "meta.json").read_text(encoding="utf-8"))
    meta.update({"stopped_by_budget": cortada_por_presupuesto,
                 "repeats_complete": integridad["repeats_complete"],
                 "complete": integridad["complete"],
                 "cells_run": len(registros), "cells_planned": len(celdas)})
    (destino / "meta.json").write_text(
        json.dumps(meta, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

    if silent_report:
        return 0
    print()
    print("%s %s · %d celda(s) · %s" % ("ensayo" if sealed else "corrida", run_id,
                                        len(registros), destino))
    if not integridad["complete"]:
        print()
        print("corrida INCOMPLETA: %d de %d repetición(es) completas en todas las filas."
              % (integridad["repeats_complete"], args.repeats))
        if integridad["repeats_complete"]:
            print("Se lee hasta la repetición %d; las celdas sueltas de la siguiente se"
                  % integridad["repeats_complete"])
            print("descartan, porque dejarían los brazos con distinto n.")
        else:
            print("Ninguna repetición quedó completa en las dos filas: no hay nada que")
            print("comparar.")
        registros = integridad["usable_records"]
    if sealed:
        return _render_sealed(registros, destino)
    return _render_report(registros, prereg, args)


def _render_sealed(registros, destino) -> int:
    """Salud de la corrida, sin el resultado. Lo que se ve acá no contamina nada."""
    salud = bench_mod.operational_summary(registros)
    print()
    print("salud del ensayo (sin resultados: el pre-registro no está congelado)")
    print("  %-16s %d de %d" % ("completadas", salud["completed"], salud["cells"]))
    print("  %-16s %.1f s en total · %.1f s la mediana"
          % ("tiempo", salud["seconds_total"], salud["seconds_median"] or 0))
    if salud.get("input_tokens") or salud.get("output_tokens"):
        print("  %-16s %s de entrada · %s de salida"
              % ("tokens", "{:,}".format(salud["input_tokens"]),
                 "{:,}".format(salud["output_tokens"])))
    if salud.get("list_price_usd_total") is not None:
        # No es una factura: con suscripción no se paga esto. Es la vara para comparar.
        print("  %-16s USD %.2f a precio de lista (una suscripción no factura esto)"
              % ("uso valorizado", salud["list_price_usd_total"]))
    if salud["tool_calls_median"] is not None:
        print("  %-16s %.1f (mediana)" % ("tool calls", salud["tool_calls_median"]))
    if salud["limit_exceeded"]:
        print("  %-16s %d celda(s) lo excedieron" % ("límite", salud["limit_exceeded"]))
    print("  %-16s %d de %d celdas produjeron dato medible"
          % ("cobertura", salud["with_outcome"], salud["cells"]))
    for fila, datos in sorted(salud.get("treated", {}).items()):
        if fila == "S0":
            continue          # S0 es el baseline: no recibe memoria de nightshift a propósito
        print("  %-16s %s: %d de %d celdas de MEDICIÓN recibieron memoria%s"
              % ("tratamiento", fila, datos["with_memory"], datos["cells"],
                 "  ← el tratamiento no se aplicó" if not datos["with_memory"] else ""))
    if salud["errors"]:
        print()
        print("celdas con problema:")
        for item in salud["errors"]:
            print("  %-3s %-16s %s" % (item["row"], item["task"], item["error"]))
    print()
    sin_tratar = [f for f, d in salud.get("treated", {}).items()
                  if f != "S0" and d["cells"] and not d["with_memory"]]
    if sin_tratar:
        print("la fila %s no recibió memoria en ninguna celda: la comparación no mediría"
              % ", ".join(sin_tratar))
        print("nada. Arreglalo antes de congelar.")
    elif salud["errored"] or salud["with_outcome"] < salud["cells"]:
        print("el ensayo encontró problemas: arreglalos antes de congelar nada.")
    else:
        print("la máquina corre entera. Lo que midió queda sellado hasta que el")
        print("pre-registro se congele: verlo ahora le pondría un incentivo a los")
        print("umbrales, que es lo que el pre-registro existe para impedir.")
    print()
    print("resultados en %s/results.jsonl · `bench report --unseal` los muestra" % destino)
    return 1 if (salud["errored"] or sin_tratar) else 0


def _bench_report(args, prereg) -> int:
    base = _bench_dir()
    corridas = sorted([d for d in base.glob("*") if (d / "results.jsonl").is_file()]) \
        if base.is_dir() else []
    if not corridas:
        print("no hay corridas registradas. `nightshift bench run` las produce.",
              file=sys.stderr)
        return 1
    elegida = base / args.run if args.run else corridas[-1]
    if not (elegida / "results.jsonl").is_file():
        print("no encuentro la corrida %s" % args.run, file=sys.stderr)
        return 1
    registros = [json.loads(line) for line in
                 (elegida / "results.jsonl").read_text(encoding="utf-8").splitlines() if line]
    meta = {}
    if (elegida / "meta.json").is_file():
        meta = json.loads((elegida / "meta.json").read_text(encoding="utf-8"))
    if not getattr(args, "json", False):
        print("corrida: %s%s" % (elegida.name, "  (ensayo)" if meta.get("rehearsal") else ""))
    if meta.get("rehearsal") and not getattr(args, "unseal", False):
        print()
        print("es un ensayo, y sus resultados están sellados. Se corrió sin pre-registro")
        print("congelado, así que mirarlos ahora es elegir los umbrales sabiendo el")
        print("efecto. `--unseal` los muestra igual, y deja dicho que se los vio.")
        return _render_sealed(registros, elegida)
    if meta.get("rehearsal"):
        print()
        print("⚠  ensayo DESSELLADO. Si el pre-registro todavía no estaba congelado,")
        print("   anotalo en su registro de enmiendas: quien fije los umbrales ya vio esto.")
    return _render_report(registros, prereg, args)


def _render_report(registros, prereg, args) -> int:
    resumen = bench_mod.summarize(registros)
    veredicto = bench_mod.decide(resumen, prereg)

    if getattr(args, "json", False):
        json.dump({"summary": [v for v in resumen.values()], "decision": veredicto,
                   "records": registros}, sys.stdout, indent=2, ensure_ascii=False)
        sys.stdout.write("\n")
        return 0

    print()
    print("resultados (mediana por celda; se publican todas las corridas, PREREG §4):")
    print("  %-8s %-4s %-6s %-8s %-16s %-10s %s" % ("familia", "fila", "corr.", "tareas",
                                                    "resolución", "tool calls", "uso (lista)"))
    costo_total = 0.0
    excedidas = 0
    timeouts = 0
    for clave in sorted(resumen):
        item = resumen[clave]
        rango = item["resolution_rate_range"]
        costo_total += item["cost_usd"] or 0.0
        excedidas += item["limit_exceeded"]
        timeouts += item["timed_out"]
        print("  %-8s %-4s %-6d %-8d %-16s %-10s %s" % (
            item["family"], item["row"], item["runs"], item["n"],
            "—" if item["resolution_rate"] is None else "%.2f [%.2f–%.2f]" % (
                item["resolution_rate"], rango[0], rango[1]),
            "—" if item["tool_calls_median"] is None else "%.1f" % item["tool_calls_median"],
            "—" if item["cost_usd"] is None else "%.2f" % item["cost_usd"]))
    if costo_total:
        print("  %-8s %s" % ("total", "USD %.2f a precio de lista" % costo_total))
    if excedidas:
        print()
        print("  %d celda(s) excedieron el límite de tool calls. El CLI no lo puede"
              % excedidas)
        print("  imponer (no expone `--max-turns`): se midió, no se cortó.")
    if timeouts:
        print()
        print("  %d celda(s) no terminaron por timeout: el agente no llegó a completar"
              % timeouts)
        print("  la tarea. Cuentan como no resueltas igual que un fallo, pero no es lo")
        print("  mismo — no se sabe si las habría resuelto con más tiempo. Buscá "
              "[TIMEOUT] abajo.")

    print()
    print("corridas individuales:")
    for record in registros:
        detalle = record.get("error") or ""
        if record.get("timed_out"):
            detalle = "[TIMEOUT] %s" % detalle
        print("  %-3s c%d %-6s %-8s gate %s→%s  resuelto=%-5s %s" % (
            record["row"], record["repeat"], record["task"], record["phase"],
            record.get("gate_before"), record.get("gate_after"), record.get("resolved"),
            detalle))

    print()
    print("regla de decisión (PREREG §1): %s" % veredicto["regla"])
    for family, item in sorted(veredicto["por_familia"].items()):
        print("  familia %s · %s" % (family, item["label"]))
        print("      S0=%s  S1=%s  umbral=%s  →  %s" % (
            "—" if item["S0"] is None else "%.3f" % item["S0"],
            "—" if item["S1"] is None else "%.3f" % item["S1"],
            item["threshold"] or "sin fijar",
            {True: "alcanza", False: "no alcanza", None: "indecidible"}[item["met"]]))
    print()
    if veredicto["go"] is None:
        print("veredicto: INDECIDIBLE — falta(n) umbral(es) para %s."
              % ", ".join(veredicto["indecidibles"]))
        print("Indecidible no es no-go, y sobre todo no es go.")
        return 1
    print("veredicto: %s (%d de 3 familias alcanzan el umbral)"
          % ("GO" if veredicto["go"] else "NO-GO", len(veredicto["familias_alcanzadas"])))
    print("La tolerancia de regresión sigue siendo un TODO(Matias): esa mitad de la")
    print("regla no se evaluó.")
    return 0


SELFTEST_PREREG = """# PREREG SINTÉTICO — sólo para el selftest del runner

| Campo | Valor |
|---|---|
| Estado | CONGELADO (sintético) |

Los números de acá son inventados para probar el runner. **No son los umbrales de M4**:
ésos viven en bench/PREREG.md, están sin fijar, y los fija Matías.

### A — Bug recurrente variado

| Métrica | Umbral de go (S1 vs S0) |
|---|---|
| Tasa de resolución | +20 pp |

### C — Transferencia cross-repo

| Métrica | Umbral de go (S1 vs S0) |
|---|---|
| Tasa de resolución en repo B | +20 pp |

### D — Precisión de consolidación

| Métrica | Umbral de go (S1 vs S0) |
|---|---|
| Proporción de memorias falsas o stale | -10 pp |
"""


def _bench_selftest(args) -> int:
    """Gate del runner: matriz → ejecución → gate → clasificador → resumen → decisión.

    Con fixtures sintéticos y un agente falso, en un directorio temporal. **No prueba que
    nightshift sirva** — eso es lo que M4 mide, y M4 no puede correr todavía porque su
    pre-registro no está congelado. Prueba que el runner no miente cuando le toque.
    """
    import shutil as _shutil

    failures = []
    with tempfile.TemporaryDirectory(prefix="nightshift-bench-") as tmp:
        raiz = Path(tmp)
        trabajo = raiz / "fixture"
        _shutil.copytree(SELFTEST_FIXTURE, trabajo)
        prereg_path = raiz / "PREREG-sintetico.md"
        prereg_path.write_text(SELFTEST_PREREG, encoding="utf-8")

        # 1. Sobre el pre-registro REAL, correr tiene que estar prohibido.
        real = bench_mod.read_prereg(PREREG_PATH)
        if bench_mod.readiness(real)["ready"]:
            failures.append("el pre-registro real se declaró listo, y tiene TODO(Matias) "
                            "sin resolver y dice BORRADOR")
        print("  el pre-registro real no está listo: `run` se niega  ✓")

        prereg = bench_mod.read_prereg(prereg_path)
        estado = bench_mod.readiness(prereg)
        if not estado["ready"]:
            failures.append("el pre-registro sintético debería alcanzar para correr: %s"
                            % "; ".join(estado["blockers"]))

        # 2. El pipeline entero, las tres familias.
        registros = []
        previous = os.environ.get("NIGHTSHIFT_HOME")
        os.environ["NIGHTSHIFT_HOME"] = str(raiz / "home")
        try:
            config.init(force=True)
            for familia in ("a", "c", "d"):
                class _Args:
                    fixture = str(trabajo / ("fixture-%s.json" % familia))
                    agent = "./agent.sh {task} {row}"
                    rows = "S0,S1"
                    repeats = 2
                    seed = "selftest"
                    timeout = 60
                    json = False
                    run = None
                _bench_run(_Args(), prereg, estado, quiet=True, silent_report=True)
            for corrida in sorted((raiz / "home" / "bench").glob("*")):
                registros.extend(json.loads(line) for line in
                                 (corrida / "results.jsonl").read_text(encoding="utf-8")
                                 .splitlines() if line)
        finally:
            if previous is None:
                os.environ.pop("NIGHTSHIFT_HOME", None)
            else:
                os.environ["NIGHTSHIFT_HOME"] = previous

        resumen = bench_mod.summarize(registros)
        veredicto = bench_mod.decide(resumen, prereg)

        if len(registros) != 48:
            failures.append("esperaba 48 celdas (3 familias × 2 filas × 2 corridas × 4 "
                            "tareas), hubo %d" % len(registros))
        aprendizaje = [r for r in registros if r["phase"] == "learning"]
        if len(aprendizaje) != 24:
            failures.append("esperaba 24 celdas de aprendizaje (la mitad), hubo %d"
                            % len(aprendizaje))
        if any(r["phase"] == "learning" and r["task_index"] >= 2 for r in registros):
            failures.append("la fase de aprendizaje son las primeras tareas del orden fijo")
        for familia in ("A", "C"):
            s0 = (resumen.get((familia, "S0")) or {}).get("resolution_rate")
            s1 = (resumen.get((familia, "S1")) or {}).get("resolution_rate")
            if s0 is None or s1 is None:
                failures.append("familia %s: falta la tasa de resolución de alguna fila"
                                % familia)
            elif not s1 > s0:
                failures.append("familia %s: el agente falso resuelve más en S1 y el "
                                "resumen no lo refleja" % familia)
        d_s1 = (resumen.get(("D", "S1")) or {}).get("false_stale_ratio")
        if d_s1 is None:
            failures.append("familia D: el clasificador del fixture no dejó "
                            "`false_stale_ratio` en el resumen")
        if veredicto["go"] is not True:
            failures.append("con las tres familias medidas y umbrales fijados, el "
                            "veredicto debería ser GO y fue %s" % veredicto["go"])
        print("  pipeline completo: %d celdas, 3 familias, veredicto=%s  ✓"
              % (len(registros), {True: "GO", False: "NO-GO"}.get(veredicto["go"], "?")))

        # 3. En D, menor es mejor: si S1 empeora, la familia NO alcanza.
        peor = dict(resumen)
        peor[("D", "S1")] = dict(resumen[("D", "S1")], false_stale_ratio=0.9)
        if bench_mod.decide(peor, prereg)["por_familia"]["D"]["met"] is not False:
            failures.append("en la familia D menor es mejor: empeorar no puede alcanzar "
                            "el umbral")
        print("  en D menor es mejor: empeorar no alcanza el umbral  ✓")

        # 4. Sin una familia medida, el veredicto es indecidible: nunca go.
        parcial = {k: v for k, v in resumen.items() if k[0] != "C"}
        if bench_mod.decide(parcial, prereg)["go"] is not None:
            failures.append("con una familia sin medir el veredicto tiene que ser "
                            "indecidible")
        # 5. Y sin umbrales, también.
        if bench_mod.decide(resumen, real)["go"] is not None:
            failures.append("sin umbrales el veredicto tiene que ser indecidible")
        print("  sin una familia, o sin umbrales: indecidible, nunca go  ✓")

        # 6. La fila S2 es de M5 y M5 está bloqueado.
        try:
            bench_mod.matrix(bench_mod.load_fixture(str(trabajo / "fixture-a.json")),
                             rows=("S0", "S2"))
            failures.append("la fila S2 se dejó planificar y M5 está bloqueado")
        except ValueError:
            pass
        print("  la fila S2 (M5) se rechaza  ✓")

        # 7. El pre-registro real no se tocó.
        if "TODO(Matias)" not in PREREG_PATH.read_text(encoding="utf-8"):
            failures.append("FUGA DE PROCESO: el pre-registro real perdió sus TODO(Matias)")
        print("  el pre-registro real sigue con sus TODO(Matias) intactos  ✓")

    print()
    if failures:
        for item in failures:
            print("  FALLA  %s" % item)
        print("bench --selftest: %d fallo(s)" % len(failures))
        return 1
    print("bench --selftest: OK — el runner corre entero con un pre-registro congelado,")
    print("se niega con el real, y ante un dato o un umbral que falta dice indecidible")
    print("en vez de adivinar.")
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

    next_run = getattr(chosen, "next_run", None)

    if args.json:
        json.dump({
            "backend_elegido": chosen.name,
            "instalados": [{"backend": b.name, "unit": str(b.unit_path)} for b in instalados],
            "entorno": sched.environment(),
            "corridas": [dict(row) for row in runs],
            "proxima_corrida": next_run().isoformat() if next_run else None,
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
    if next_run:
        print("próxima    : %s" % next_run().strftime("%Y-%m-%d %H:%M"))
    print("comando    : %s" % " ".join(chosen.command()))
    if instalados:
        for item in instalados:
            print("instalado  : %s → %s" % (item.name, item.unit_path))
    else:
        print("instalado  : no. `nightshift schedule install` lo deja programado.")
    print()
    if runs:
        # La última columna es USD **a precio de lista**: la vara para comparar una
        # corrida con otra, no lo que se factura. Con una suscripción de Claude Code no
        # se paga eso, y una columna titulada "costo" haría creer que sí.
        print("últimas corridas:%s" % (" " * 62 + "USD lista"))
        for row in runs:
            veredicto = {0: "ok", 1: "no consolidó", 2: "sin modelo local"}.get(
                row["exit_code"], "exit=%s" % row["exit_code"])
            costo = row["cost_usd"] if "cost_usd" in row.keys() else None
            print("  %s  %-8s %-9s %-16s cand=%d sup=%d desc=%d %s %s" % (
                row["started_at"], row["command"], row["backend"] or "—", veredicto,
                row["candidates"] or 0, row["superseded"] or 0, row["rejected"] or 0,
                ("%.3f" % costo) if costo else "        ",
                (row["note"] or "")[:50]))
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

    # La invariante que faltaba, y la más cara: una trayectoria con pasos de tool y
    # ninguno con contenido significa que la captura se rompió. Pasó durante dos
    # milestones sin que nada lo dijera (spec §5.9).
    try:
        conn = store.connect()
        try:
            calidad = store.capture_quality(conn)
        finally:
            conn.close()
        ultima = calidad["latest"]
        if not ultima:
            detalle, ok = "todavía no hay una trayectoria con pasos de tool", True
        elif not ultima["healthy"]:
            # El doctor afirma sobre el presente. Que haya trayectorias viejas rotas es
            # historia y lo cuenta `status`; que la última lo esté es un bug ahora.
            detalle = ("la última trayectoria (%s) tiene %d pasos de tool y ninguno con "
                       "contenido" % (ultima["trajectory"][:8], ultima["tool_steps"]))
            ok = False
        else:
            detalle = ("última: %d pasos de tool, %d sin contenido"
                       % (ultima["tool_steps"], ultima["hollow"]))
            ok = True
        checks.append(_check("la captura trae contenido", ok, detalle))
    except Exception as exc:
        checks.append(_check("la captura trae contenido", False, str(exc)))

    # Qué modelo consolida, y qué implica. Con ADR-003 el default manda lo redactado
    # fuera de la máquina: eso tiene que verse en la herramienta, no sólo en un ADR.
    try:
        from . import dream as dream_mod

        backend = cfg.get("model_backend", "claude-code")
        comando = dream_mod.detect_command(cfg)
        if comando:
            detalle = "%s · %s" % (
                backend,
                "lo redactado sale de la máquina (ADR-003)" if backend == "claude-code"
                else "nada sale de la máquina")
        else:
            detalle = "backend `%s` sin ejecutable: dream no puede consolidar" % backend
        checks.append(_check("backend de consolidación", bool(comando), detalle))
    except Exception as exc:
        checks.append(_check("backend de consolidación", False, str(exc)))

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
# Payloads con la forma **real** de Claude Code, sondeada el 2026-08-26 (spec §5.9). Que
# el selftest usara nombres de campo inventados es la razón por la que pasó en verde
# durante todo M1 y M2 mientras la captura llegaba vacía en las sesiones de verdad.
REPLAY = [
    ("SessionStart", {"session_id": "selftest", "cwd": ".", "source": "startup"}),
    ("UserPromptSubmit", {"session_id": "selftest", "cwd": ".",
                          "prompt": "los tests fallan con UnicodeDecodeError"}),
    ("PostToolUse", {"session_id": "selftest", "cwd": ".", "tool_name": "Read",
                     "tool_use_id": "t1", "tool_input": {"file_path": "/tmp/x/parser.py"},
                     "tool_response": {"type": "text", "file": "def parse(data): ..."}}),
    ("PostToolUseFailure", {"session_id": "selftest", "cwd": ".", "tool_name": "Bash",
                            "tool_use_id": "t2", "is_interrupt": False,
                            "tool_input": {"command": "pytest -q",
                                           "env": {"API_TOKEN": "tok_live_selftest_999"}},
                            "error": "UnicodeDecodeError: 'utf-8' codec can't decode"}),
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
                    # Un paso capturado sin contenido es una captura que no capturó. Pasó:
                    # con los nombres de campo equivocados, todos los pasos quedaban vacíos
                    # y el selftest seguía en verde porque sólo miraba la estructura.
                    vacios = [s for s in doc["steps"] if s["kind"] in ("tool_use", "tool_failure")
                              and not (s["result_summary"] or s["error_message"])]
                    if vacios:
                        failures.append("%d paso(s) de tool sin resumen ni error: la "
                                        "captura llegó vacía" % len(vacios))
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
    print("milestone actual: M3 completo · M4 con runner y sin resultados")
    print("  hecho     : captura, redactor, store, retrieval, /why, audit, dream fase 1,")
    print("              scheduler, y el runner de M4 — que se niega a correr")
    print("  falta     : congelar PREREG (19 TODO(Matias)) y correr M4; después, M5 verify")
    print("  evidencia : el gate de M1 pide 2 sesiones más; el de M3, tres noches")
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
    p.add_argument("--max-groups", type=int, default=None,
                   help="consolidar como mucho N grupos esta corrida: cada grupo llama"
                        " al modelo y, con el backend claude-code, cobra (ADR-003)")
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

    p = sub.add_parser("bench", help="runner del benchmark de M4 (lee los umbrales, no los fija)")
    p.add_argument("action", nargs="?", default="check",
                   choices=("check", "plan", "run", "rehearse", "report", "fixtures",
                            "selftest"))
    p.add_argument("--fixture", default=None, help="ruta a un fixture.json")
    p.add_argument("--agent", default=None,
                   help="comando del agente por tarea; admite {prompt} {task} {row}")
    p.add_argument("--rows", default="S0,S1", help="filas a correr (S2 es de M5)")
    p.add_argument("--repeats", type=int, default=3)
    p.add_argument("--seed", default=None)
    p.add_argument("--timeout", type=int, default=600)
    p.add_argument("--budget-minutes", type=float, default=None,
                   help="tope de tiempo de pared para la corrida entera. Corta al "
                        "terminar una repetición, nunca en el medio")
    p.add_argument("--prereg", default=None, help="pre-registro alternativo (para pruebas)")
    p.add_argument("--run", default=None, help="id de corrida para `report`")
    p.add_argument("--unseal", action="store_true",
                   help="mostrar los resultados de un ensayo; deja dicho que se los vio")
    p.add_argument("--limit", type=int, default=24)
    p.add_argument("--json", action="store_true")
    p.set_defaults(func=cmd_bench)

    p = sub.add_parser("simulate",
                       help="ensayo end-to-end con sesiones sintéticas (no cierra gates)")
    p.add_argument("--nights", type=int, default=3, help="corridas nocturnas simuladas")
    p.add_argument("--no-model", action="store_true",
                   help="saltar dream: para máquinas sin modelo local")
    p.add_argument("--dump", help="escribir el reporte completo a este archivo JSON")
    p.set_defaults(func=cmd_simulate)

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
