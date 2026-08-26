#!/usr/bin/env python3
"""Clasifica la memoria inyectada contra el ground truth. Determinista, sin modelo.

PREREG §3-D: "La clasificación falsa/stale la hace un script determinista contra un
ground truth construido a mano al preparar el fixture, no un modelo". Esto es ese script.

Emite `NIGHTSHIFT_BENCH {"false_stale_ratio": x}` con la proporción de memorias
inyectadas que son falsas o stale.

**Sólo puede medir la fila S1.** En S0 nightshift no está, y las memorias que inyecta
Auto Memory no son visibles desde acá. Cómo se enumeran esas es un `TODO(Matias)` del
pre-registro; mientras no exista, S0 no emite dato y la familia D queda indecidible en
el reporte. Eso es correcto: mejor sin veredicto que con uno inventado.
"""

import json
import os
import pathlib
import re
import sqlite3
import sys

RAIZ = pathlib.Path(__file__).resolve().parent
STORE = pathlib.Path(os.environ.get("NIGHTSHIFT_BENCH_WORKDIR", str(RAIZ))) / ".store"
CLAIM_RE = re.compile(r"claim:(\w+)")


def main():
    if os.environ.get("NIGHTSHIFT_BENCH_ROW") == "S0":
        print("S0 no tiene inyecciones de nightshift que enumerar: sin dato "
              "(TODO(Matias) en PREREG §3-D)", file=sys.stderr)
        return 0

    db = STORE / "trajectories.sqlite3"
    if not db.is_file():
        print("no hay store sembrado en %s" % STORE, file=sys.stderr)
        return 1
    verdad = json.loads((RAIZ / "verdad.json").read_text(encoding="utf-8"))

    conn = sqlite3.connect(str(db))
    conn.row_factory = sqlite3.Row
    inyectadas = conn.execute(
        "SELECT DISTINCT source_trajectory FROM injections").fetchall()
    total = malas = 0
    detalle = []
    for fila in inyectadas:
        pasos = conn.execute(
            "SELECT result_summary FROM steps WHERE trajectory_id = ?",
            (fila["source_trajectory"],)).fetchall()
        claims = {m.group(1) for paso in pasos
                  for m in [CLAIM_RE.search(paso["result_summary"] or "")] if m}
        for claim in sorted(claims):
            estado = verdad.get(claim, {}).get("estado", "desconocida")
            total += 1
            if estado in ("falsa", "stale"):
                malas += 1
            detalle.append({"claim": claim, "estado": estado})
    conn.close()

    if not total:
        print("no se inyectó ninguna memoria con claim conocido", file=sys.stderr)
        return 0
    print("NIGHTSHIFT_BENCH %s" % json.dumps(
        {"false_stale_ratio": round(malas / total, 4), "inyectadas": total,
         "falsas_o_stale": malas, "detalle": detalle}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
