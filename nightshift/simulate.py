"""Ensayo end-to-end: sesiones sintéticas por el camino real de captura.

Qué es esto y qué **no** es, porque la diferencia es el proyecto entero:

**Es** un ensayo del sistema completo — captura por los 7 hooks, redacción, `deny_paths`,
huérfanas, retrieval en dos pasadas, auditoría, consolidación con el modelo local,
scheduler y registro de corridas — sobre un store desechable. Sirve para responder
"¿funciona la máquina de punta a punta?" hoy, sin esperar semanas de uso.

**No es** evidencia para los gates de M1 ni de M3. El gate de M1 pide *5 sesiones reales
capturadas*; el de M3, *tres noches seguidas sin intervención*. Una sesión sintética no
es una sesión real y tres corridas seguidas en un bucle no son tres noches: no hay
suspensión, ni batería, ni un launchd que se olvidó de disparar, que es exactamente lo
que esos gates miden. Correr esto y anotarlo como gate cerrado sería fabricar evidencia.

Por eso el ensayo corre en un `NIGHTSHIFT_HOME` temporal y **nunca toca el store real**:
no se puede cerrar un gate de sesiones reales inflando el conteo con sesiones inventadas.
"""

from __future__ import annotations

import contextlib
import io
import json
import os
import tempfile
from pathlib import Path

from . import audit, config, context, hook, store
from .redact import Redactor

SECRETO = "tok_live_simulacion_no_debe_sobrevivir_999"

# Sesiones sintéticas. Cada una es una historia con forma de sesión real: un prompt que
# la clasifica, tool calls, a veces un fallo decisivo, a veces una corrección del usuario.
SESIONES = [
    {
        "id": "sim-01-debug-ok",
        "prompt": "los tests fallan con UnicodeDecodeError al leer el fixture",
        "pasos": [
            ("PostToolUse", {"tool_name": "Bash", "tool_input": {"command": "pytest -q"},
                             "tool_output": "3 failed"}),
            ("PostToolUseFailure", {"tool_name": "Bash",
                                    "tool_input": {"command": "pytest -q tests/test_parser.py"},
                                    "error_message": "UnicodeDecodeError: 'utf-8' codec"}),
            ("PostToolUse", {"tool_name": "Read", "tool_input": {"file_path": "src/parser.py"},
                             "tool_output": "def load(path): return open(path).read()"}),
            ("PostToolUse", {"tool_name": "Edit", "tool_input": {"file_path": "src/parser.py"},
                             "tool_output": "encoding declarado"}),
            ("PostToolUse", {"tool_name": "Bash", "tool_input": {"command": "pytest -q"},
                             "tool_output": "42 passed"}),
        ],
    },
    {
        "id": "sim-02-debug-corregida",
        "prompt": "otra vez fallan los tests, ahora en el borde del pipeline",
        "pasos": [
            ("PostToolUse", {"tool_name": "Edit", "tool_input": {"file_path": "src/pipe.py"},
                             "tool_output": "try/except agregado"}),
            ("UserPromptSubmit", {"user_input": "no, eso está mal: tapaste el error"}),
            ("PostToolUse", {"tool_name": "Bash", "tool_input": {"command": "pytest -q"},
                             "tool_output": "3 failed"}),
        ],
    },
    {
        "id": "sim-03-refactor",
        "prompt": "refactorizar la normalización duplicada en tres módulos",
        "pasos": [
            ("PostToolUse", {"tool_name": "Grep", "tool_input": {"pattern": "normalize"},
                             "tool_output": "3 coincidencias"}),
            ("PostToolUse", {"tool_name": "Edit", "tool_input": {"file_path": "src/util.py"},
                             "tool_output": "función común extraída"}),
            ("PostToolUse", {"tool_name": "Bash", "tool_input": {"command": "make test"},
                             "tool_output": "ok"}),
        ],
    },
    {
        "id": "sim-04-docs",
        "prompt": "actualizar el README con la sección de instalación",
        "pasos": [
            ("PostToolUse", {"tool_name": "Write", "tool_input": {"file_path": "README.md"},
                             "tool_output": "escrito"}),
        ],
    },
    {
        "id": "sim-05-feature-con-secreto",
        "prompt": "implementar el cliente de publicación con su token",
        "pasos": [
            # Un secreto en los argumentos: tiene que salir redactado del otro lado.
            ("PostToolUse", {"tool_name": "Bash",
                             "tool_input": {"command": "export API_TOKEN=%s && ./publicar" % SECRETO,
                                            "env": {"API_TOKEN": SECRETO}},
                             "tool_output": "publicado"}),
            # Y un archivo bajo deny_paths: no se captura ni el hecho de que ocurrió.
            ("PostToolUse", {"tool_name": "Read", "tool_input": {"file_path": ".env"},
                             "tool_output": "DB_PASSWORD=secreto-de-produccion"}),
            ("PreCompact", {"compaction_reason": "auto"}),
            ("PostToolUse", {"tool_name": "Bash", "tool_input": {"command": "pytest -q"},
                             "tool_output": "8 passed"}),
        ],
    },
    {
        "id": "sim-06-debug-parecida",
        "prompt": "el test de decodificación vuelve a fallar en otro módulo",
        "pasos": [
            ("PostToolUseFailure", {"tool_name": "Bash", "tool_input": {"command": "pytest -q"},
                                    "error_message": "UnicodeDecodeError en el lector de config"}),
            ("PostToolUse", {"tool_name": "Edit", "tool_input": {"file_path": "src/config.py"},
                             "tool_output": "encoding explícito"}),
            ("PostToolUse", {"tool_name": "Bash", "tool_input": {"command": "pytest -q"},
                             "tool_output": "todo pasa"}),
        ],
    },
]

# Una sesión que muere sin `SessionEnd`: la huérfana que T3 tiene que cerrar.
HUERFANA = {
    "id": "sim-07-muerta",
    "prompt": "los tests fallan al arrancar",
    "pasos": [
        ("PostToolUseFailure", {"tool_name": "Bash", "tool_input": {"command": "pytest -q"},
                                "error_message": "ImportError al arrancar"}),
    ],
}


def _sesion(payload_base, sesion, *, cerrar=True):
    """Una sesión completa por el camino real: los hooks, no el store."""
    base = dict(payload_base, session_id=sesion["id"])
    salida = {"session_id": sesion["id"], "inyecciones": []}

    texto, mensaje = hook.dispatch("SessionStart", dict(base))
    salida["inyeccion_session_start"] = texto
    salida["mensaje_session_start"] = mensaje

    texto = hook.dispatch("UserPromptSubmit", dict(base, user_input=sesion["prompt"]))[0]
    salida["inyeccion_primer_prompt"] = texto

    for evento, extra in sesion["pasos"]:
        hook.dispatch(evento, dict(base, **extra))
    hook.dispatch("Stop", dict(base, last_assistant_message="listo"))
    if cerrar:
        hook.dispatch("SessionEnd", dict(base))
    return salida


def run(*, cwd=None, con_modelo=True, noches=3, log=print) -> dict:
    """Corre el ensayo entero. Devuelve un reporte con los hallazgos y las fallas."""
    cwd = cwd or os.getcwd()
    fallas = []
    reporte = {"sesiones": [], "fallas": fallas}

    def afirmar(condicion, mensaje):
        if not condicion:
            fallas.append(mensaje)
        return bool(condicion)

    with tempfile.TemporaryDirectory(prefix="nightshift-sim-") as tmp:
        raiz = Path(tmp)
        previos = {k: os.environ.get(k) for k in ("NIGHTSHIFT_HOME", "HOME")}
        os.environ["NIGHTSHIFT_HOME"] = str(raiz / "store")
        os.environ["HOME"] = str(raiz / "home")
        (raiz / "home").mkdir(parents=True, exist_ok=True)
        try:
            config.init(force=True)
            base = {"cwd": cwd}

            # ---------------------------------------------------------- 1. capturar
            log("1. captura — %d sesiones sintéticas por los 7 hooks" % (len(SESIONES) + 1))
            for sesion in SESIONES:
                reporte["sesiones"].append(_sesion(base, sesion))
            _sesion(base, HUERFANA, cerrar=False)

            conn = store.connect()
            try:
                # La huérfana se envejece: T3 corta por inactividad, no por antigüedad.
                viejo = store.hours_ago(48)
                conn.execute("UPDATE trajectories SET created_at = ? WHERE session_id = ?",
                             (viejo, HUERFANA["id"]))
                conn.execute(
                    "UPDATE steps SET at = ? WHERE trajectory_id IN"
                    " (SELECT id FROM trajectories WHERE session_id = ?)",
                    (viejo, HUERFANA["id"]))
                conn.commit()

                c = store.counts(conn)
                reporte["capturado"] = c
                afirmar(c["closed"] + c["discarded"] >= len(SESIONES),
                        "no se cerraron todas las sesiones simuladas")
                afirmar(c["open"] == 1, "la huérfana debería ser la única `open`")

                # deny_paths: ni el path, ni el contenido, ni el hecho de que ocurrió.
                blob = json.dumps([dict(r) for r in conn.execute("SELECT * FROM steps")],
                                  ensure_ascii=False)
                afirmar(SECRETO not in blob, "FUGA: el secreto sobrevivió a la redacción")
                afirmar("DB_PASSWORD" not in blob,
                        "FUGA: se capturó el contenido de un archivo bajo deny_paths")
                afirmar('"file_path": ".env"' not in blob,
                        "FUGA: se capturó la ruta de un archivo bajo deny_paths")
                hits = sum(json.loads(r["redaction_json"]).get("deny_path_hits", 0)
                           for r in conn.execute("SELECT redaction_json FROM trajectories"))
                afirmar(hits >= 1, "el intento sobre un deny_path no quedó contabilizado")
                reporte["deny_path_hits"] = hits
            finally:
                conn.close()

            # ------------------------------------------------------- 2. auditoría (M1)
            log("2. auditoría — el gate de M1 sobre el store simulado")
            conn = store.connect()
            try:
                auditoria = audit.audit_store(
                    conn, redactor=Redactor(deny_paths=config.load()["deny_paths"],
                                            home_dir=str(Path.home())),
                    home_dir=str(Path.home()))
            finally:
                conn.close()
            reporte["auditoria"] = {k: auditoria[k] for k in
                                    ("sessions", "trajectories", "steps", "injections",
                                     "fields_scanned")}
            reporte["auditoria"]["findings"] = auditoria["findings"]
            afirmar(not auditoria["findings"],
                    "el auditor encontró %d hallazgo(s) en el store simulado"
                    % len(auditoria["findings"]))
            afirmar(auditoria["sessions"] >= 5,
                    "el ensayo debería producir al menos 5 sesiones distintas")

            # ------------------------------------- 3. huérfanas + retrieval en dos pasadas
            log("3. sesión nueva — huérfana cerrada, y retrieval en las dos pasadas")
            nueva = _sesion(base, {"id": "sim-08-nueva",
                                   "prompt": "los tests fallan con UnicodeDecodeError otra vez",
                                   "pasos": [("PostToolUse",
                                              {"tool_name": "Bash",
                                               "tool_input": {"command": "pytest -q"},
                                               "tool_output": "ok"})]})
            conn = store.connect()
            try:
                huerfana = conn.execute(
                    "SELECT status FROM trajectories WHERE session_id = ?",
                    (HUERFANA["id"],)).fetchone()
                afirmar(huerfana["status"] != "open",
                        "la huérfana siguió `open`: T3 no la cerró")
                reporte["huerfana"] = huerfana["status"]

                inyecciones = [dict(r) for r in
                               store.injections_for_session(conn, "sim-08-nueva")]
                reporte["inyecciones_sesion_nueva"] = inyecciones
                fuentes = [i["source_trajectory"] for i in inyecciones]
                afirmar(len(fuentes) == len(set(fuentes)),
                        "una trayectoria se inyectó dos veces en la misma sesión")
                afirmar(any("same_task_type" in i["reason"] for i in inyecciones),
                        "ninguna inyección matcheó por tipo de tarea")
            finally:
                conn.close()
            afirmar(bool(nueva["inyeccion_primer_prompt"]) or
                    any("same_task_type" in i["reason"]
                        for i in reporte["inyecciones_sesion_nueva"]),
                    "el retrieval del primer prompt no inyectó nada")

            # ----------------------------------------------------------- 4. dream (M3-a)
            if con_modelo:
                log("4. dream — consolidar")
                from . import dream as dream_mod

                comando = dream_mod.detect_command(config.load())
                if not comando:
                    fallas.append("no hay modelo local: dream no se pudo ensayar")
                else:  # pragma: no cover - depende de que la máquina tenga el modelo
                    # El HOME de verdad, no el del ensayo. El ensayo reemplaza `HOME` para
                    # no escribir un timer en el del usuario (paso 6), y el modelo lo
                    # heredaba: con el backend por defecto —un agente con credenciales en
                    # el HOME— eso lo hacía salir 1 con stderr vacío, y el ensayo lo
                    # reportaba como "dream no produjo ninguna candidata". Un rojo que
                    # acusaba a dream de un problema del ensayo.
                    modelo = dream_mod.LocalModel(comando, timeout=240,
                                                  home=previos.get("HOME"))
                    conn = store.connect()
                    try:
                        consolidado = dream_mod.consolidate(
                            conn, modelo, cfg=config.load(),
                            identifiers=context.repo_identifiers(cwd),
                            lookback_days=3650, log=lambda m: log("   %s" % m))
                        estados = dict(conn.execute(
                            "SELECT status, COUNT(*) FROM trajectories GROUP BY status"
                        ).fetchall())
                    finally:
                        conn.close()
                    reporte["dream"] = {
                        "model": consolidado["model"],
                        "candidates": consolidado["candidates"],
                        "superseded": consolidado["superseded"],
                        "rejected": consolidado["rejected"],
                        "skipped": consolidado["skipped"],
                        "estados": estados,
                    }
                    afirmar(consolidado["candidates"],
                            "dream no produjo ninguna candidata sobre el store simulado")
                    afirmar(estados.get("procedure", 0) == 0,
                            "algo llegó a `procedure` y `verify` no existe")

                # --------------------------------- 5. la candidata se inyecta y se marca
                log("5. sesión posterior — la candidata vuelve marcada como no verificada")
                posterior = _sesion(base, {
                    "id": "sim-09-posterior",
                    "prompt": "otra vez UnicodeDecodeError al leer un archivo",
                    "pasos": [("PostToolUse", {"tool_name": "Bash",
                                               "tool_input": {"command": "pytest -q"},
                                               "tool_output": "ok"})]})
                texto = (posterior["inyeccion_session_start"] or "") + \
                        (posterior["inyeccion_primer_prompt"] or "")
                reporte["texto_inyectado"] = texto
                afirmar("SIN VERIFICAR" in texto or "candidate" not in texto,
                        "se inyectó una candidata sin marcarla como no verificada")
                afirmar("Ninguna está verificada" in texto,
                        "el texto inyectado no trae el caveat de no verificación")

            # ------------------------------------------------- 6. scheduler (M3-b) y noches
            log("6. scheduler — instalar sin activar y correr %d noche(s) simulada(s)" % noches)
            from . import cli as cli_mod
            from . import schedule as sched_mod

            backend = sched_mod.backend("launchd", config.load())
            instalacion = backend.install(activate=False)
            afirmar(backend.installed(), "la unidad del scheduler no quedó escrita")
            afirmar(str(Path.home()) in instalacion["path"],
                    "la unidad se escribió fuera del HOME temporal del ensayo")

            for noche in range(1, noches + 1):
                # La corrida nocturna imprime su propio reporte. Acá interesa el veredicto,
                # no el detalle: el detalle ya se vio en el paso 4.
                #
                # Y corre con el **HOME de verdad**, por lo mismo que el paso 4: la noche
                # invoca el CLI en proceso, el CLI construye el modelo, y el modelo es un
                # agente con credenciales en el HOME (ADR-003). Con el HOME del ensayo las
                # tres noches salían 1 —"dream no consolidó: grupos descartados"— y eso se
                # leía como un problema de consolidación. El HOME de mentira hace falta
                # para el paso del scheduler, no para éste.
                buffer = io.StringIO()
                falso = os.environ["HOME"]
                if con_modelo and previos.get("HOME"):
                    os.environ["HOME"] = previos["HOME"]
                try:
                    with contextlib.redirect_stdout(buffer), contextlib.redirect_stderr(buffer):
                        codigo = cli_mod.main(["dream", "--backend", "launchd"] +
                                              ([] if con_modelo else ["--model", "/bin/echo"]))
                finally:
                    os.environ["HOME"] = falso
                resumen = [linea for linea in buffer.getvalue().splitlines()
                           if linea.startswith(("candidatas", "nada que consolidar",
                                                "el modelo no encontró", "dream no"))]
                log("   noche %d: dream salió %d · %s"
                    % (noche, codigo, resumen[0] if resumen else "sin novedades"))
            conn = store.connect()
            try:
                corridas = [dict(r) for r in store.recent_runs(conn, 10)]
            finally:
                conn.close()
            reporte["corridas"] = corridas
            afirmar(len(corridas) >= noches,
                    "esperaba %d corrida(s) registrada(s), hay %d" % (noches, len(corridas)))
            afirmar(all(r["exit_code"] in (0, 1) for r in corridas),
                    "alguna corrida nocturna falló por falta de modelo (exit 2)")

            # --------------------------------------------- 7. el store sigue sin fugas
            log("7. auditoría final — después de dream y de las corridas")
            conn = store.connect()
            try:
                final = audit.audit_store(
                    conn, redactor=Redactor(deny_paths=config.load()["deny_paths"],
                                            home_dir=str(Path.home())),
                    home_dir=str(Path.home()))
            finally:
                conn.close()
            reporte["auditoria_final"] = {"findings": final["findings"],
                                          "fields_scanned": final["fields_scanned"],
                                          "runs": final["runs"]}
            afirmar(not final["findings"],
                    "el auditor encontró %d hallazgo(s) después de dream"
                    % len(final["findings"]))
        finally:
            for clave, valor in previos.items():
                if valor is None:
                    os.environ.pop(clave, None)
                else:
                    os.environ[clave] = valor

    return reporte
