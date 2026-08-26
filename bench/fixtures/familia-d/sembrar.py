#!/usr/bin/env python3
"""Siembra la historia de la familia D en un store de nightshift para esta celda.

El store va en `.store/` dentro del directorio de trabajo de la celda, así que cada
celda arranca con exactamente la misma historia y ninguna hereda la de la anterior.

Escribe SQL directo a propósito: el fixture representa "un histórico que ya existía", no
una sesión que nightshift acaba de capturar.
"""

import json
import os
import pathlib
import sqlite3
import sys
import uuid
from datetime import datetime, timedelta, timezone

RAIZ = pathlib.Path(__file__).resolve().parent
DESTINO = pathlib.Path(os.environ.get("NIGHTSHIFT_BENCH_STORE")
                       or (pathlib.Path(os.environ.get("NIGHTSHIFT_BENCH_WORKDIR",
                                                       str(RAIZ))) / ".store"))
FINGERPRINT = "d" * 64


def main():
    sys.path.insert(0, os.environ.get("NIGHTSHIFT_ROOT", ""))
    try:
        from nightshift import store
    except ImportError:
        print("no encuentro el paquete nightshift: fijá NIGHTSHIFT_ROOT", file=sys.stderr)
        return 2

    DESTINO.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(DESTINO / "trajectories.sqlite3"))
    conn.executescript(store.SCHEMA_SQL)

    historia = json.loads((RAIZ / "historia.json").read_text(encoding="utf-8"))
    ahora = datetime.now(timezone.utc)
    for i, item in enumerate(historia):
        tid = str(uuid.uuid4())
        creado = (ahora - timedelta(days=len(historia) - i)).strftime("%Y-%m-%dT%H:%M:%SZ")
        conn.execute(
            "INSERT INTO trajectories (id, created_at, closed_at, status, harness_name,"
            " session_id, repo_fingerprint, task_type, outcome_result, injection_weight,"
            " redaction_json) VALUES (?,?,?,'closed','claude-code',?,?,?,?,0.3,?)",
            (tid, creado, creado, "historia-%s" % item["id"], FINGERPRINT,
             item["task_type"], item["outcome"],
             json.dumps({"redactor_version": "0.1.0"})))
        conn.execute(
            "INSERT INTO steps (trajectory_id, idx, at, kind, tool, result_summary,"
            " decisive, contradicted) VALUES (?,0,?,'observation','run_shell',?,1,?)",
            (tid, creado, "claim:%s · %s" % (item["claim"], item["resumen"]),
             1 if item["outcome"] == "user_corrected" else 0))
    conn.commit()
    conn.close()
    print("sembradas %d trayectorias en %s" % (len(historia), DESTINO))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
