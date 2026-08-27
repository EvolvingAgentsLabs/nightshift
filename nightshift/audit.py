"""Auditoría del store persistido. Es el gate de M1.

El gate de M1 dice: *5 sesiones reales capturadas sin fuga de `deny_paths`, con un test
automatizado sobre el dump*. Este módulo es ese test, corrido sobre todo lo persistido y
no sobre una sesión de juguete.

Afirma cinco cosas sobre cada cadena del store:

1. ninguna matchea un patrón de `deny_paths` (spec §8.1);
2. ningún patrón de `redact.SECRET_RULES` matchea — si el redactor dejó pasar un
   secreto, acá se ve (spec §8.2);
3. no sobrevive ninguna ruta absoluta del home del usuario;
4. no hay rutas bajo el árbol de Auto Memory (spec §1.3.4);
5. `abstraction.pattern` no contiene secuencias tipo path (spec §4.4).

**El reporte no imprime el material que encontró.** Dice dónde (trayectoria, paso,
campo), qué regla saltó, y en qué posición del valor — nunca el valor. Un reporte de
auditoría que cita la fuga la propaga a la terminal, al scrollback y al pipe de quien lo
corrió.

Un auditor que nunca falla no es un auditor: `tests/test_audit.py` siembra una fuga de
cada clase en un store desechable y afirma que ésta las encuentra.
"""

from __future__ import annotations

import json
import re

from . import config
from .redact import SECRET_RULES

# Espejo de `abstraction.pattern.not.pattern` en schema/trajectory.v1.json. El esquema es
# la fuente de verdad; `test_audit.py` afirma que estas dos cadenas no se separaron.
ABSTRACTION_PATH_PATTERN = r"(~/|\.\./|/[A-Za-z0-9_.\-]+/)"
ABSTRACTION_PATH_RE = re.compile(ABSTRACTION_PATH_PATTERN)

# Home de cualquier usuario, no sólo el de esta máquina: el store puede venir de otra.
HOME_PATH_RE = re.compile(r"(?:/Users|/home|/root)/[A-Za-z0-9_.\-]+(?:/|\b)")

# Tokens que parecen ruta, para poder pasarlos por `deny_paths` uno por uno. Sin esto una
# fuga embebida en prosa ("abrí /home/x/proj/.env y decía…") no matchearía ningún patrón,
# porque `fnmatch` compara la cadena entera.
#
# El token exige un separador de directorio a propósito. Un nombre suelto (`.env` escrito
# en un comentario, `credentials` en una oración) es una **mención**, no una ruta: sin esa
# condición el auditor marcaba su propio código fuente capturado. La cadena completa sigue
# pasando por `is_denied` con la misma semántica que usó el redactor al capturar, así que
# un valor que *es* `.env` se sigue detectando.
PATH_TOKEN_RE = re.compile(
    r"~?(?:/[A-Za-z0-9_.\-]+)+/?"                # /a/b/c  ·  ~/a/b
    r"|(?:[A-Za-z0-9_.\-]+/)+[A-Za-z0-9_.\-]*")  # a/b/c relativo

# Lo que deja el redactor cuando hace su trabajo. Un placeholder no es una fuga: es la
# prueba de que la regla corrió. `secret.assignment` volvería a matchear `TOKEN=<SECRET>`
# si no lo dijéramos explícitamente.
PLACEHOLDER_RE = re.compile(r"<(?:SECRET|PATH|REPO|EMAIL|BLOB|CREDENTIALS|TRUNCATED)>")

# Nombre de campo seguro para imprimir. Una clave de diccionario puede ser ella misma el
# material que estamos auditando (`{"/home/x/.env": …}`), así que sólo se imprime si es
# un identificador corto y anodino.
SAFE_KEY_RE = re.compile(r"^[A-Za-z0-9_\-]{1,32}$")

# Columnas SQL que guardan JSON, con el nombre que ese campo tiene en trajectory.v1.
JSON_COLUMNS = {
    "abstraction_json": "abstraction",
    "valid_when_json": "valid_when",
    "projected_signals_json": "projected_signals",
    "contrast_json": "contrast",
    "verified_json": "verified",
    "redaction_json": "redaction",
    "args_json": "args_redacted",
}


def _safe_key(key) -> str:
    key = str(key)
    return key if SAFE_KEY_RE.match(key) else "<clave>"


def _strings(value, prefix):
    """Emite `(campo, cadena)` por cada string dentro de `value`, claves incluidas.

    Las claves se emiten como valores auditables (una clave puede ser una ruta) pero
    nunca se interpolan crudas en el nombre del campo.
    """
    if isinstance(value, dict):
        for key, item in value.items():
            field = "%s.%s" % (prefix, _safe_key(key))
            yield field, str(key)
            for found in _strings(item, field):
                yield found
    elif isinstance(value, list):
        for i, item in enumerate(value):
            for found in _strings(item, "%s[%d]" % (prefix, i)):
                yield found
    elif isinstance(value, str):
        yield prefix, value


def _is_placeholder(text) -> bool:
    text = text.strip().strip("\"'")
    return bool(PLACEHOLDER_RE.fullmatch(text))


def scan_value(value, field, *, redactor, home_dir=None):
    """Devuelve los hallazgos de una sola cadena. Nunca devuelve el valor."""
    findings = []
    if not isinstance(value, str) or not value:
        return findings

    def add(rule, start, length):
        findings.append({"rule": rule, "field": field, "pos": int(start), "len": int(length)})

    for name, pattern in SECRET_RULES:
        for match in pattern.finditer(value):
            payload = match.group(3) if name == "secret.assignment" else match.group(0)
            if _is_placeholder(payload):
                continue
            add(name, match.start(), len(match.group(0)))
            break

    if redactor.is_denied(value):
        add("deny_path", 0, len(value))
    else:
        for match in PATH_TOKEN_RE.finditer(value):
            if redactor.is_denied(match.group(0)):
                add("deny_path", match.start(), len(match.group(0)))
                break

    match = HOME_PATH_RE.search(value)
    if match:
        add("home_path", match.start(), len(match.group(0)))
    elif home_dir and home_dir in value:
        add("home_path", value.index(home_dir), len(home_dir))

    match = config.AUTO_MEMORY_RE.search(value.replace("\\", "/"))
    if match:
        add("auto_memory", match.start(), len(match.group(0)))

    if field.endswith("abstraction.pattern"):
        match = ABSTRACTION_PATH_RE.search(value)
        if match:
            add("abstraction_path", match.start(), len(match.group(0)))

    return findings


def _scan_row(row, *, prefix, redactor, home_dir, skip=()):
    """Escanea todas las columnas de una fila, parseando las que guardan JSON."""
    findings = []
    scanned = 0
    for column in row.keys():
        if column in skip:
            continue
        value = row[column]
        if value is None:
            continue
        name = JSON_COLUMNS.get(column, column)
        field = "%s.%s" % (prefix, name)
        if column in JSON_COLUMNS:
            try:
                parsed = json.loads(value)
            except (TypeError, ValueError):
                pairs = [(field, str(value))]
            else:
                pairs = list(_strings(parsed, field))
        elif isinstance(value, str):
            pairs = [(field, value)]
        else:
            continue
        for item_field, text in pairs:
            scanned += 1
            findings.extend(scan_value(text, item_field, redactor=redactor, home_dir=home_dir))
    return findings, scanned


def audit_store(conn, *, redactor, home_dir=None) -> dict:
    """Audita todo lo persistido. `redactor` aporta los `deny_paths` vigentes."""
    findings = []
    scanned = 0

    for row in conn.execute("SELECT * FROM trajectories ORDER BY created_at, rowid"):
        tid = row["id"]
        found, count = _scan_row(row, prefix="trajectory", redactor=redactor,
                                 home_dir=home_dir, skip=("id",))
        scanned += count
        for item in found:
            item.update({"trajectory": tid, "step": None})
        findings.extend(found)

        for step in conn.execute(
                "SELECT * FROM steps WHERE trajectory_id = ? ORDER BY idx", (tid,)):
            found, count = _scan_row(step, prefix="steps[%d]" % step["idx"], redactor=redactor,
                                     home_dir=home_dir, skip=("trajectory_id",))
            scanned += count
            for item in found:
                item.update({"trajectory": tid, "step": int(step["idx"])})
            findings.extend(found)

    for row in conn.execute("SELECT * FROM injections ORDER BY at"):
        found, count = _scan_row(row, prefix="injection[%d]" % row["id"], redactor=redactor,
                                 home_dir=home_dir, skip=("id",))
        scanned += count
        for item in found:
            item.update({"trajectory": row["source_trajectory"], "step": None})
        findings.extend(found)

    for row in conn.execute("SELECT * FROM runs ORDER BY id"):
        found, count = _scan_row(row, prefix="run[%d]" % row["id"], redactor=redactor,
                                 home_dir=home_dir, skip=("id",))
        scanned += count
        for item in found:
            item.update({"trajectory": None, "step": None})
        findings.extend(found)

    # Determinista: mismo store, mismo orden de hallazgos.
    findings.sort(key=lambda f: (f["trajectory"] or "", f["step"] if f["step"] is not None else -1,
                                 f["field"], f["rule"], f["pos"]))

    sessions = conn.execute(
        "SELECT COUNT(DISTINCT session_id) AS c FROM trajectories"
        " WHERE session_id IS NOT NULL AND session_id != ''").fetchone()["c"]

    # Sesiones que además **capturaron algo**. El gate de M1 pide 5 sesiones reales sin
    # fuga de `deny_paths`, y una sesión cuyos pasos están vacíos no es evidencia de eso:
    # no se puede filtrar lo que nunca se guardó. Auditar cáscaras da un verde vacío.
    #
    # Se descubrió contando mal: durante dos milestones la captura guardó estructura sin
    # contenido (spec §5.9), y el conteo de sesiones no lo distinguía.
    with_content = conn.execute(
        "SELECT COUNT(DISTINCT t.session_id) AS c FROM trajectories t"
        " WHERE t.session_id IS NOT NULL AND t.session_id != '' AND EXISTS ("
        "   SELECT 1 FROM steps s WHERE s.trajectory_id = t.id"
        "   AND s.kind IN ('tool_use','tool_failure')"
        "   AND (COALESCE(s.result_summary,'') != '' OR COALESCE(s.error_message,'') != '')"
        ")").fetchone()["c"]
    trajectories = conn.execute("SELECT COUNT(*) AS c FROM trajectories").fetchone()["c"]
    steps = conn.execute("SELECT COUNT(*) AS c FROM steps").fetchone()["c"]
    injections = conn.execute("SELECT COUNT(*) AS c FROM injections").fetchone()["c"]
    runs = conn.execute("SELECT COUNT(*) AS c FROM runs").fetchone()["c"]

    return {
        "sessions": int(sessions),
        "sessions_with_content": int(with_content),
        "trajectories": int(trajectories),
        "steps": int(steps),
        "injections": int(injections),
        "runs": int(runs),
        "fields_scanned": scanned,
        "deny_paths": len(redactor.deny_paths),
        "findings": findings,
    }
