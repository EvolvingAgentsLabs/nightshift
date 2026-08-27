"""Persistencia local en SQLite.

Todo lo que entra acá ya pasó por el redactor. El store nunca contiene material sin
redactar (spec §8.2), y nunca vive bajo el árbol de Auto Memory (`config.guard_path`).

El esquema SQL es interno. El contrato público es `export_trajectory()`, que emite un
objeto que valida contra `schema/trajectory.v1.json` — el mismo archivo que M0 congeló.
"""

from __future__ import annotations

import json
import sqlite3
import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path

from . import SCHEMA_VERSION, config

SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS meta (
    key TEXT PRIMARY KEY,
    value TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS trajectories (
    id TEXT PRIMARY KEY,
    created_at TEXT NOT NULL,
    closed_at TEXT,
    status TEXT NOT NULL,
    harness_name TEXT NOT NULL,
    harness_version TEXT,
    session_id TEXT,
    repo_fingerprint TEXT NOT NULL,
    task_type TEXT NOT NULL,
    hypothesis TEXT,
    base_commit TEXT,
    outcome_result TEXT,
    outcome_gate_id TEXT,
    outcome_evidence TEXT,
    abstraction_json TEXT,
    valid_when_json TEXT,
    consolidation_model TEXT,
    consolidation_cost_usd REAL,
    ideation TEXT,
    projected_signals_json TEXT,
    superseded_by TEXT,
    verified_json TEXT,
    injection_weight REAL,
    redaction_json TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS steps (
    trajectory_id TEXT NOT NULL,
    idx INTEGER NOT NULL,
    at TEXT NOT NULL,
    kind TEXT NOT NULL,
    tool TEXT,
    tool_native TEXT,
    tool_use_id TEXT,
    args_json TEXT,
    result_summary TEXT,
    error_message TEXT,
    state_delta TEXT,
    decisive INTEGER NOT NULL DEFAULT 0,
    contradicted INTEGER NOT NULL DEFAULT 0,
    PRIMARY KEY (trajectory_id, idx)
);
CREATE TABLE IF NOT EXISTS injections (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    at TEXT NOT NULL,
    session_id TEXT,
    into_trajectory TEXT,
    source_trajectory TEXT NOT NULL,
    rank INTEGER NOT NULL,
    score REAL NOT NULL,
    reason TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS runs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    started_at TEXT NOT NULL,
    finished_at TEXT,
    command TEXT NOT NULL,
    backend TEXT,
    exit_code INTEGER,
    trajectories INTEGER,
    candidates INTEGER,
    superseded INTEGER,
    rejected INTEGER,
    cost_usd REAL,
    note TEXT
);
CREATE INDEX IF NOT EXISTS idx_runs_started ON runs(started_at);
CREATE INDEX IF NOT EXISTS idx_traj_session ON trajectories(session_id);
CREATE INDEX IF NOT EXISTS idx_traj_task ON trajectories(task_type, status);
CREATE INDEX IF NOT EXISTS idx_inj_session ON injections(session_id);
"""

SCHEMA_REVISION = "3"


def now() -> str:
    """Marca de tiempo UTC con resolución de **segundos**.

    Ancho fijo para poder comparar con `<` en SQL, y por eso mismo dos filas creadas en
    el mismo segundo empatan. Todo `ORDER BY created_at` lleva `rowid` de desempate: sin
    eso "la última trayectoria" es indefinida, y con dos trayectorias del mismo segundo
    SQLite devuelve la que quiera. Lo encontró un test que abría dos seguidas.
    """
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


# Columnas agregadas después de la primera versión del esquema. `CREATE TABLE IF NOT
# EXISTS` no toca una tabla que ya existe, así que un store viejo se queda sin ellas para
# siempre y falla al escribir. Migrar es agregar lo que falte, y nada más: nunca se borra
# ni se reescribe una columna con datos.
COLUMNAS_AGREGADAS = {
    "runs": [("cost_usd", "REAL")],
    "trajectories": [("consolidation_model", "TEXT"), ("consolidation_cost_usd", "REAL"),
                     ("ideation", "TEXT"), ("projected_signals_json", "TEXT")],
}


def migrate(conn):
    """Agrega las columnas que le falten a un store viejo. Idempotente."""
    agregadas = []
    for tabla, columnas in COLUMNAS_AGREGADAS.items():
        existentes = {fila["name"] for fila in
                      conn.execute("PRAGMA table_info(%s)" % tabla).fetchall()}
        for nombre, tipo in columnas:
            if nombre not in existentes:
                conn.execute("ALTER TABLE %s ADD COLUMN %s %s" % (tabla, nombre, tipo))
                agregadas.append("%s.%s" % (tabla, nombre))
    if agregadas:
        conn.commit()
    return agregadas


def hours_ago(hours: float) -> str:
    """Marca de tiempo de hace N horas, en el mismo formato que `now()`.

    Los timestamps son ISO-8601 UTC de ancho fijo, así que comparar con `<` en SQL es
    comparar fechas. Cambiar el formato de `now()` rompe eso en silencio.
    """
    then = datetime.now(timezone.utc) - timedelta(hours=float(hours))
    return then.strftime("%Y-%m-%dT%H:%M:%SZ")


def connect(path: Path | None = None) -> sqlite3.Connection:
    target = config.guard_path(path or config.db_path())
    target.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(target), timeout=2.0)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA synchronous=NORMAL")
    conn.executescript(SCHEMA_SQL)
    migrate(conn)
    conn.execute(
        "INSERT OR REPLACE INTO meta(key, value) VALUES ('schema_revision', ?)",
        (SCHEMA_REVISION,),
    )
    conn.commit()
    return conn


# ------------------------------------------------------------------ trayectorias
def open_trajectory(conn, *, session_id, repo_fingerprint, task_type, harness_name="claude-code",
                    harness_version=None, base_commit=None, hypothesis=None, redaction=None):
    tid = str(uuid.uuid4())
    conn.execute(
        "INSERT INTO trajectories (id, created_at, status, harness_name, harness_version,"
        " session_id, repo_fingerprint, task_type, hypothesis, base_commit, redaction_json,"
        " injection_weight) VALUES (?,?,?,?,?,?,?,?,?,?,?,?)",
        (tid, now(), "open", harness_name, harness_version, session_id, repo_fingerprint,
         task_type, hypothesis, base_commit,
         json.dumps(redaction or {"redactor_version": "0.0.0"}), 0.3),
    )
    conn.commit()
    return tid


def active_trajectory(conn, session_id):
    row = conn.execute(
        "SELECT * FROM trajectories WHERE session_id = ? AND status = 'open'"
        " ORDER BY created_at DESC, rowid DESC LIMIT 1", (session_id,)).fetchone()
    return row


def append_step(conn, trajectory_id, *, kind, tool=None, tool_native=None, tool_use_id=None,
                args=None, result_summary=None, error_message=None, state_delta=None,
                decisive=False, max_steps=400):
    """Agrega un paso al final. El índice se calcula **dentro** del INSERT.

    Antes eran dos sentencias: leer `MAX(idx)` y después insertar `idx + 1`. Con dos
    hooks corriendo a la vez —que es lo que pasa en cuanto el agente lanza tool calls en
    paralelo— los dos leían el mismo máximo, los dos intentaban el mismo índice, y el
    segundo moría con `UNIQUE constraint failed`. El hook salía 0 igual, así que la
    sesión no se enteraba: el paso simplemente no quedaba.

    Con `INSERT ... SELECT`, el índice y la inserción son una sola sentencia y SQLite las
    serializa. El tope de pasos viaja en el `HAVING` por el mismo motivo: si se comprueba
    aparte, se comprueba sobre un número que ya cambió.
    """
    cursor = conn.execute(
        "INSERT INTO steps (trajectory_id, idx, at, kind, tool, tool_native, tool_use_id,"
        " args_json, result_summary, error_message, state_delta, decisive, contradicted)"
        " SELECT ?, COALESCE(MAX(idx), -1) + 1, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 0"
        " FROM steps WHERE trajectory_id = ? HAVING COUNT(*) < ?",
        (trajectory_id, now(), kind, tool, tool_native, tool_use_id,
         json.dumps(args, ensure_ascii=False) if args is not None else None,
         result_summary, error_message, state_delta, 1 if decisive else 0,
         trajectory_id, max_steps),
    )
    conn.commit()
    if not cursor.rowcount:
        return None
    row = conn.execute("SELECT idx FROM steps WHERE rowid = ?",
                       (cursor.lastrowid,)).fetchone()
    return int(row["idx"]) if row else None


def mark_last_contradicted(conn, trajectory_id):
    """Marca el paso anterior como contradicho (hook UserPromptSubmit).

    Una sola sentencia, por el mismo motivo que `append_step`: entre leer cuál es el
    último y marcarlo puede aparecer otro.
    """
    cursor = conn.execute(
        "UPDATE steps SET contradicted = 1 WHERE trajectory_id = ?"
        " AND idx = (SELECT MAX(idx) FROM steps WHERE trajectory_id = ?)",
        (trajectory_id, trajectory_id))
    conn.commit()
    if not cursor.rowcount:
        return None
    row = conn.execute("SELECT MAX(idx) AS m FROM steps WHERE trajectory_id = ?"
                       " AND contradicted = 1", (trajectory_id,)).fetchone()
    return int(row["m"]) if row and row["m"] is not None else None


def stale_open_trajectories(conn, *, cutoff, exclude_session=None, limit=50):
    """Trayectorias `open` sin actividad desde `cutoff`, de otras sesiones.

    "Sin actividad" es el último paso, no la fecha de apertura: una sesión de doce horas
    sigue apendeando pasos, y cerrarle la trayectoria por debajo la partiría en dos —
    exactamente lo que spec §5.6 evita al no cerrar en `Stop`.
    """
    return conn.execute(
        "SELECT * FROM trajectories AS t WHERE t.status = 'open'"
        " AND (? IS NULL OR t.session_id IS NULL OR t.session_id != ?)"
        " AND COALESCE((SELECT MAX(s.at) FROM steps AS s WHERE s.trajectory_id = t.id),"
        "              t.created_at) < ?"
        " ORDER BY t.created_at, t.rowid LIMIT ?",
        (exclude_session, exclude_session, cutoff, limit)).fetchall()


def close_trajectory(conn, trajectory_id, *, result, gate_id=None, evidence=None, redaction=None):
    status = "closed" if result != "abandoned" else "discarded"
    fields = [status, now(), result, gate_id, evidence]
    sql = ("UPDATE trajectories SET status = ?, closed_at = ?, outcome_result = ?,"
           " outcome_gate_id = ?, outcome_evidence = ?")
    if redaction is not None:
        sql += ", redaction_json = ?"
        fields.append(json.dumps(redaction))
    sql += " WHERE id = ?"
    fields.append(trajectory_id)
    conn.execute(sql, fields)
    conn.commit()
    return status


# --------------------------------------------------------------- corridas (M3-b)
def record_run(conn, *, command, backend=None, started_at=None, exit_code=None,
               trajectories=0, candidates=0, superseded=0, rejected=0, cost_usd=None,
               note=None):
    """Registra una corrida de dream. Es lo que `schedule status` tiene para mostrar.

    Sin esto, un scheduler es una promesa: hay un timer, y nadie sabe si la última noche
    hizo algo. `note` viene redactado desde quien llama — un mensaje de error del modelo
    es texto no controlado como cualquier otro.
    """
    conn.execute(
        "INSERT INTO runs (started_at, finished_at, command, backend, exit_code,"
        " trajectories, candidates, superseded, rejected, cost_usd, note)"
        " VALUES (?,?,?,?,?,?,?,?,?,?,?)",
        (started_at or now(), now(), command, backend, exit_code, trajectories,
         candidates, superseded, rejected, cost_usd, note))
    conn.commit()


def recent_runs(conn, limit=10):
    return conn.execute("SELECT * FROM runs ORDER BY started_at DESC, id DESC LIMIT ?",
                        (limit,)).fetchall()


# ------------------------------------------------------------------- dream (M3)
def promote_to_candidate(conn, trajectory_id, *, abstraction, valid_when, hypothesis=None,
                         weight=0.6, consolidation_model=None, consolidation_cost_usd=None,
                         ideation=None, projected_signals=None):
    """`closed` → `candidate`, con la abstracción que produjo dream fase 1.

    No es `procedure`: nada llega ahí sin `verified`, y `verify` es M5. El peso de
    inyección baja a propósito respecto de un procedimiento verificado (spec §6.3).

    `ideation` es el boceto del mecanismo del que salió la abstracción, y
    `projected_signals` son síntomas que este mecanismo **produciría** y que nadie
    observó. Los dos se guardan aparte de `abstraction` justamente porque no son lo
    mismo: `signals` se vio, `projected_signals` se anticipó. Mezclarlos sería subir
    una conjetura a la categoría de observación, y el retrieval las pesa distinto.

    `consolidation_model` y `consolidation_cost_usd` son la respuesta a "¿con qué se
    abstrajo esto y cuánto costó?" — sin registrarlos por trayectoria, la condición de
    éxito 3 (auditabilidad, spec §1.3) queda a medias: `why` reconstruye el patrón pero
    no de dónde salió. `consolidation_cost_usd` en `None` significa que el backend no
    reportó costo (p.ej. un modelo local), no que haya costado cero.
    """
    # `hypothesis` sólo se escribe si dream infirió una y la trayectoria no tenía: la
    # captura nunca la pobló (no se persiste texto del prompt), así que éste es el único
    # momento en que puede aparecer, y no puede pisar algo declarado antes.
    conn.execute(
        "UPDATE trajectories SET status = 'candidate', abstraction_json = ?,"
        " valid_when_json = ?, injection_weight = ?,"
        " hypothesis = COALESCE(hypothesis, ?), consolidation_model = ?,"
        " consolidation_cost_usd = ?, ideation = ?, projected_signals_json = ?"
        " WHERE id = ? AND status = 'closed'",
        (json.dumps(abstraction, ensure_ascii=False),
         json.dumps(valid_when or [], ensure_ascii=False), weight, hypothesis,
         consolidation_model, consolidation_cost_usd, ideation,
         json.dumps(projected_signals, ensure_ascii=False) if projected_signals else None,
         trajectory_id))
    conn.commit()
    return conn.execute("SELECT status FROM trajectories WHERE id = ?",
                        (trajectory_id,)).fetchone()["status"]


def mark_superseded(conn, old_id, new_id):
    """La vieja sobrevive enlazada a la nueva. **Nunca se borra** (capacidad B).

    Auto Dream borra lo contradicho; nosotros lo conservamos, porque una alternativa
    descartada con su precondición es conocimiento y sin ella es ruido (spec §4.2).
    """
    if old_id == new_id:
        return None
    conn.execute(
        "UPDATE trajectories SET status = 'superseded', superseded_by = ? WHERE id = ?",
        (new_id, old_id))
    conn.commit()
    return new_id


def record_injection(conn, *, session_id, source_trajectory, rank, score, reason,
                     into_trajectory=None):
    conn.execute(
        "INSERT INTO injections (at, session_id, into_trajectory, source_trajectory, rank,"
        " score, reason) VALUES (?,?,?,?,?,?,?)",
        (now(), session_id, into_trajectory, source_trajectory, rank, score, reason),
    )
    conn.commit()


def injected_sources(conn, session_id):
    """Ids ya inyectados en esta sesión.

    El retrieval corre dos veces (`SessionStart` y el primer `UserPromptSubmit` con tipo
    de tarea), así que hace falta saber qué se dijo ya: repetir una trayectoria gasta
    contexto y hace pasar por dos evidencias lo que es una sola.
    """
    rows = conn.execute(
        "SELECT DISTINCT source_trajectory FROM injections WHERE session_id = ?",
        (session_id,)).fetchall()
    return {row["source_trajectory"] for row in rows}


def injections_for_session(conn, session_id):
    return conn.execute("SELECT * FROM injections WHERE session_id = ? ORDER BY rank",
                        (session_id,)).fetchall()


def injections_of_source(conn, source_trajectory):
    return conn.execute(
        "SELECT * FROM injections WHERE source_trajectory = ? ORDER BY at DESC",
        (source_trajectory,)).fetchall()


def get_trajectory(conn, trajectory_id):
    row = conn.execute("SELECT * FROM trajectories WHERE id = ?", (trajectory_id,)).fetchone()
    if row is None:
        row = conn.execute("SELECT * FROM trajectories WHERE id LIKE ? LIMIT 2",
                           (trajectory_id + "%",)).fetchall()
        if len(row) != 1:
            return None
        row = row[0]
    return row


def steps_of(conn, trajectory_id):
    return conn.execute("SELECT * FROM steps WHERE trajectory_id = ? ORDER BY idx",
                        (trajectory_id,)).fetchall()


def capture_quality(conn, limit=20):
    """Qué tan buena es la captura de las últimas trayectorias, en números.

    Existe por una razón concreta: durante M1 y M2 la captura guardó 223 pasos sin una
    sola línea de contenido y **nadie se enteró**, porque los hooks salen 0 pase lo que
    pase (spec §7.2). El modo de fallo de este plugin es el silencio, así que hay que
    mirarlo a propósito: nada te lo va a decir.
    """
    filas = conn.execute(
        "SELECT id FROM trajectories ORDER BY created_at DESC, rowid DESC LIMIT ?",
        (limit,)).fetchall()
    ids = [f["id"] for f in filas]
    if not ids:
        return {"trajectories": 0, "tool_steps": 0, "hollow": 0, "decisive": 0,
                "hollow_ratio": None, "decisive_ratio": None, "unmapped": 0,
                "broken": [], "worst": None, "latest": None}
    marcas = ",".join("?" * len(ids))
    pasos = conn.execute(
        "SELECT trajectory_id, kind, tool, decisive,"
        " (COALESCE(result_summary,'') = '' AND COALESCE(error_message,'') = '') AS vacio"
        " FROM steps WHERE trajectory_id IN (%s)" % marcas, ids).fetchall()
    de_tool = [p for p in pasos if p["kind"] in ("tool_use", "tool_failure")]
    huecos = [p for p in de_tool if p["vacio"]]

    # La peor trayectoria: la que tiene pasos de tool y ninguno con contenido. Eso no es
    # "poca calidad", es la captura rota.
    por_trayectoria = {}
    for paso in de_tool:
        celda = por_trayectoria.setdefault(paso["trajectory_id"], [0, 0])
        celda[0] += 1
        celda[1] += 1 if paso["vacio"] else 0
    rotas = [tid for tid, (total, vacios) in por_trayectoria.items()
             if total >= 3 and total == vacios]

    # La última trayectoria con pasos de tool es la que dice si la captura funciona
    # **ahora**. Las viejas son historia: una captura que se rompió y se arregló no puede
    # dejar al doctor en rojo para siempre.
    ultima = None
    for tid in ids:                                   # ids viene en orden descendente
        if tid in por_trayectoria and por_trayectoria[tid][0] >= 3:
            total, vacios = por_trayectoria[tid]
            ultima = {"trajectory": tid, "tool_steps": total, "hollow": vacios,
                      "healthy": vacios < total}
            break
    return {
        "latest": ultima,
        "trajectories": len(ids),
        "tool_steps": len(de_tool),
        "hollow": len(huecos),
        "decisive": sum(1 for p in pasos if p["decisive"]),
        "hollow_ratio": (len(huecos) / len(de_tool)) if de_tool else None,
        "decisive_ratio": (sum(1 for p in pasos if p["decisive"]) / len(pasos)) if pasos else None,
        "unmapped": sum(1 for p in pasos if p["tool"] == "other"),
        "broken": rotas,
        "worst": rotas[0] if rotas else None,
    }


def counts(conn):
    out = {}
    for status in ("open", "closed", "candidate", "procedure", "superseded", "discarded"):
        out[status] = conn.execute("SELECT COUNT(*) c FROM trajectories WHERE status = ?",
                                   (status,)).fetchone()["c"]
    out["steps"] = conn.execute("SELECT COUNT(*) c FROM steps").fetchone()["c"]
    out["injections"] = conn.execute("SELECT COUNT(*) c FROM injections").fetchone()["c"]
    return out


def store_size_bytes(path: Path | None = None) -> int:
    """Tamaño en disco del store: el archivo principal más los sidecars de WAL

    (`-wal`, `-shm`), que `connect()` deja activo (spec: sin política de retención
    todavía, LATER.md). Sin los sidecars el número subestima lo que realmente ocupa
    un store con escrituras recientes sin checkpointear.
    """
    target = path or config.db_path()
    total = 0
    for suffix in ("", "-wal", "-shm"):
        candidate = Path(str(target) + suffix)
        if candidate.is_file():
            total += candidate.stat().st_size
    return total


# --------------------------------------------------------------------- exportar
def export_trajectory(conn, trajectory_id) -> dict | None:
    """Emite el objeto que valida contra schema/trajectory.v1.json."""
    row = get_trajectory(conn, trajectory_id)
    if row is None:
        return None
    tid = row["id"]
    doc = {
        "schema_version": SCHEMA_VERSION,
        "id": tid,
        "created_at": row["created_at"],
        "closed_at": row["closed_at"],
        "status": row["status"],
        "harness": {"name": row["harness_name"]},
        "repo_fingerprint": row["repo_fingerprint"],
        "task_type": row["task_type"],
        "hypothesis": row["hypothesis"],
        "base_commit": row["base_commit"],
        "steps": [],
        "outcome": None,
        "abstraction": json.loads(row["abstraction_json"]) if row["abstraction_json"] else None,
        "valid_when": json.loads(row["valid_when_json"]) if row["valid_when_json"] else [],
        "superseded_by": row["superseded_by"],
        "verified": json.loads(row["verified_json"]) if row["verified_json"] else None,
        "redaction": json.loads(row["redaction_json"]),
    }
    if row["harness_version"]:
        doc["harness"]["version"] = row["harness_version"]
    if row["session_id"]:
        doc["harness"]["session_id"] = row["session_id"]
    if row["injection_weight"] is not None:
        doc["injection_weight"] = row["injection_weight"]
    if row["outcome_result"]:
        doc["outcome"] = {
            "result": row["outcome_result"],
            "gate_id": row["outcome_gate_id"],
            "evidence": row["outcome_evidence"],
        }
    for step in steps_of(conn, tid):
        item = {
            "index": step["idx"],
            "at": step["at"],
            "kind": step["kind"],
            "tool": step["tool"],
            "tool_native": step["tool_native"],
            "tool_use_id": step["tool_use_id"],
            "args_redacted": json.loads(step["args_json"]) if step["args_json"] else None,
            "result_summary": step["result_summary"],
            "error_message": step["error_message"],
            "state_delta": step["state_delta"],
            "decisive": bool(step["decisive"]),
            "contradicted": bool(step["contradicted"]),
        }
        doc["steps"].append(item)
    return doc
