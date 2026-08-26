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
from datetime import datetime, timezone
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
CREATE INDEX IF NOT EXISTS idx_traj_session ON trajectories(session_id);
CREATE INDEX IF NOT EXISTS idx_traj_task ON trajectories(task_type, status);
CREATE INDEX IF NOT EXISTS idx_inj_session ON injections(session_id);
"""

SCHEMA_REVISION = "1"


def now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def connect(path: Path | None = None) -> sqlite3.Connection:
    target = config.guard_path(path or config.db_path())
    target.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(target), timeout=2.0)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA synchronous=NORMAL")
    conn.executescript(SCHEMA_SQL)
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
        " ORDER BY created_at DESC LIMIT 1", (session_id,)).fetchone()
    return row


def append_step(conn, trajectory_id, *, kind, tool=None, tool_native=None, tool_use_id=None,
                args=None, result_summary=None, error_message=None, state_delta=None,
                decisive=False, max_steps=400):
    row = conn.execute("SELECT COALESCE(MAX(idx), -1) AS m FROM steps WHERE trajectory_id = ?",
                       (trajectory_id,)).fetchone()
    idx = int(row["m"]) + 1
    if idx >= max_steps:
        return None
    conn.execute(
        "INSERT INTO steps (trajectory_id, idx, at, kind, tool, tool_native, tool_use_id,"
        " args_json, result_summary, error_message, state_delta, decisive, contradicted)"
        " VALUES (?,?,?,?,?,?,?,?,?,?,?,?,0)",
        (trajectory_id, idx, now(), kind, tool, tool_native, tool_use_id,
         json.dumps(args, ensure_ascii=False) if args is not None else None,
         result_summary, error_message, state_delta, 1 if decisive else 0),
    )
    conn.commit()
    return idx


def mark_last_contradicted(conn, trajectory_id):
    """Marca el paso anterior como contradicho (hook UserPromptSubmit)."""
    row = conn.execute("SELECT MAX(idx) AS m FROM steps WHERE trajectory_id = ?",
                       (trajectory_id,)).fetchone()
    if row is None or row["m"] is None:
        return None
    conn.execute("UPDATE steps SET contradicted = 1 WHERE trajectory_id = ? AND idx = ?",
                 (trajectory_id, row["m"]))
    conn.commit()
    return int(row["m"])


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


def record_injection(conn, *, session_id, source_trajectory, rank, score, reason,
                     into_trajectory=None):
    conn.execute(
        "INSERT INTO injections (at, session_id, into_trajectory, source_trajectory, rank,"
        " score, reason) VALUES (?,?,?,?,?,?,?)",
        (now(), session_id, into_trajectory, source_trajectory, rank, score, reason),
    )
    conn.commit()


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


def counts(conn):
    out = {}
    for status in ("open", "closed", "candidate", "procedure", "superseded", "discarded"):
        out[status] = conn.execute("SELECT COUNT(*) c FROM trajectories WHERE status = ?",
                                   (status,)).fetchone()["c"]
    out["steps"] = conn.execute("SELECT COUNT(*) c FROM steps").fetchone()["c"]
    out["injections"] = conn.execute("SELECT COUNT(*) c FROM injections").fetchone()["c"]
    return out


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
