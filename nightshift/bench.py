"""Runner del benchmark de M4 (spec §10, `bench/PREREG.md`).

**Este módulo no decide nada.** Lee los umbrales de `bench/PREREG.md`, y si el
pre-registro no está congelado o le falta un umbral, **se niega a correr**. Un umbral
que se ajusta después de ver el resultado no es un umbral, y un runner que corre con el
pre-registro abierto es la forma más cómoda de ajustarlo sin darse cuenta.

Lo que sí hace:

- **`readiness()`** — lee el estado del pre-registro y lista qué falta, con sección y
  línea. Es lo que convierte "faltan cosas" en "faltan estas 19".
- **`matrix()`** — la grilla del experimento: familia × fila × repetición × tarea, en
  orden fijo por seed, idéntico en todas las filas (mitigación de §5).
- **`run_cell()`** — prepara la tarea, corre el agente, corre el gate del fixture. El
  criterio de resolución es el gate: sale 0 ahora y salía ≠ 0 antes. Sin juicio de
  modelo.
- **`summarize()` / `render()`** — mediana y rango por celda, y **todas** las corridas,
  incluidas las que salieron mal. Sin selección post-hoc (§4).
- **`decide()`** — aplica la regla de §1 tal cual está escrita. Si falta un umbral
  devuelve `None`: indecidible no es no-go, y sobre todo no es go.

Lo que **no** hace, y no es una omisión: fijar un umbral, proponer uno, rellenar un
`TODO(Matias)`, elegir el modelo, elegir el seed, ni re-correr buscando una
configuración mejor.

Gramática de umbrales que entiende. **Vive acá, no en el pre-registro**, porque el
formato es cosa del runner y el número es cosa de Matías:

    +10 pp      diferencia en puntos porcentuales (S1 - S0)
    -15 %       cambio relativo respecto de S0
    >= 0.30     valor absoluto de la métrica en S1  (también <=, ≥, ≤)
    TODO(...)   sin fijar

Cualquier otra cosa **no se adivina**: se reporta como umbral ilegible y bloquea la
corrida.
"""

from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
import time
from pathlib import Path

TODO_RE = re.compile(r"TODO\(([A-Za-zÁ-úñÑ]+)\)")
FROZEN_RE = re.compile(r"^\|\s*Estado\s*\|\s*(.+?)\s*\|", re.M)
SECTION_RE = re.compile(r"^#{1,3}\s+(.+?)\s*$", re.M)

FAMILIES = ("A", "C", "D")
ROWS = ("S0", "S1")            # S2 es de M5, y M5 está bloqueado hasta el veredicto de M4
BLOCKED_ROWS = {"S2": "la fila S2 (verificados) es de M5, y M5 está bloqueado hasta que "
                      "M4 dé veredicto (spec §11)"}

# Métricas primarias por familia, según §3 del pre-registro. La dirección importa: en D
# menor es mejor, y un runner que lo confunda declara go donde hay no-go.
PRIMARY = {
    "A": {"metric": "resolution_rate", "better": "higher",
          "label": "tasa de resolución (fase de medición)"},
    "C": {"metric": "resolution_rate", "better": "higher",
          "label": "tasa de resolución en repo B"},
    "D": {"metric": "false_stale_ratio", "better": "lower",
          "label": "proporción de memorias falsas o stale"},
}


# --------------------------------------------------------------------- pre-registro
class Threshold:
    def __init__(self, raw, kind, value):
        self.raw = raw
        self.kind = kind      # "pp" | "pct" | "gte" | "lte"
        self.value = value

    def __repr__(self):
        return "Threshold(%r, %s, %s)" % (self.raw, self.kind, self.value)

    def met(self, s0, s1, *, better):
        """¿La diferencia S1 vs S0 alcanza el umbral? `None` si falta un dato."""
        if s1 is None or (self.kind in ("pp", "pct") and s0 is None):
            return None
        if self.kind == "pp":
            diff = (s1 - s0) * 100.0
            return diff >= self.value if better == "higher" else diff <= self.value
        if self.kind == "pct":
            if not s0:
                return None
            diff = (s1 - s0) / abs(s0) * 100.0
            return diff >= self.value if better == "higher" else diff <= self.value
        if self.kind == "gte":
            return s1 >= self.value
        if self.kind == "lte":
            return s1 <= self.value
        return None


def parse_threshold(raw):
    """Un umbral, o `None` si no está fijado o no se entiende. Nunca se adivina."""
    if raw is None:
        return None
    text = raw.strip().replace("−", "-")
    if not text or TODO_RE.search(text):
        return None
    match = re.fullmatch(r"([+-]?\d+(?:[.,]\d+)?)\s*(pp|p\.p\.|puntos?)", text, re.I)
    if match:
        return Threshold(raw, "pp", float(match.group(1).replace(",", ".")))
    match = re.fullmatch(r"([+-]?\d+(?:[.,]\d+)?)\s*%", text)
    if match:
        return Threshold(raw, "pct", float(match.group(1).replace(",", ".")))
    match = re.fullmatch(r"(>=|≥|<=|≤)\s*(\d+(?:[.,]\d+)?)\s*%?", text)
    if match:
        kind = "gte" if match.group(1) in (">=", "≥") else "lte"
        return Threshold(raw, kind, float(match.group(2).replace(",", ".")))
    return None


def read_prereg(path) -> dict:
    """Estado del pre-registro: congelado o no, qué falta y qué umbrales tiene."""
    text = Path(path).read_text(encoding="utf-8")
    estado = FROZEN_RE.search(text)
    estado_raw = estado.group(1).strip() if estado else "(sin estado)"
    frozen = "congelado" in estado_raw.lower() and "no congelado" not in estado_raw.lower()

    seccion = "(encabezado)"
    todos = []
    for numero, linea in enumerate(text.splitlines(), start=1):
        titulo = SECTION_RE.match(linea)
        if titulo:
            seccion = titulo.group(1)
            continue
        for match in TODO_RE.finditer(linea):
            todos.append({"section": seccion, "line": numero, "owner": match.group(1),
                          "text": " ".join(linea.split())[:140]})

    # Umbrales: las tablas "| métrica | umbral |" dentro de cada familia.
    umbrales = {}
    familia = None
    for linea in text.splitlines():
        titulo = SECTION_RE.match(linea)
        if titulo:
            match = re.match(r"^([ACD])\s+—", titulo.group(1))
            familia = match.group(1) if match else None
            continue
        if not familia or not linea.startswith("|"):
            continue
        celdas = [c.strip() for c in linea.strip("|").split("|")]
        if len(celdas) != 2 or celdas[0].lower().startswith("métrica") or set(celdas[0]) <= set("- "):
            continue
        umbrales.setdefault(familia, []).append({"metric": celdas[0], "raw": celdas[1],
                                                 "threshold": parse_threshold(celdas[1])})
    return {"path": str(path), "estado": estado_raw, "frozen": frozen, "todos": todos,
            "thresholds": umbrales}


def primary_threshold(prereg, family):
    """El umbral de la métrica primaria de la familia: la primera fila de su tabla (§3)."""
    filas = prereg["thresholds"].get(family) or []
    return filas[0] if filas else None


def readiness(prereg) -> dict:
    """Qué impide correr. Vacío = se puede correr."""
    blockers = []
    if not prereg["frozen"]:
        blockers.append("el pre-registro no está congelado (Estado: %s). Se congela "
                        "**antes** de correr nada." % prereg["estado"])
    if prereg["todos"]:
        dueños = sorted({t["owner"] for t in prereg["todos"]})
        blockers.append("quedan %d TODO(%s) sin resolver. Los resuelve una persona: "
                        "completar uno es una violación, no una ayuda."
                        % (len(prereg["todos"]), "/".join(dueños)))
    for familia in FAMILIES:
        fila = primary_threshold(prereg, familia)
        if fila is None:
            blockers.append("familia %s: no encontré su tabla de umbrales" % familia)
        elif fila["threshold"] is None:
            blockers.append("familia %s: el umbral primario no está fijado o no se "
                            "entiende (%r)" % (familia, fila["raw"]))
    return {"ready": not blockers, "blockers": blockers}


# ------------------------------------------------------------------------- fixtures
REQUIRED_FIXTURE_KEYS = ("name", "family", "gate", "tasks")


class FixtureError(ValueError):
    pass


def load_fixture(path) -> dict:
    """Carga y **valida** un fixture. Un fixture mal formado no se corre a medias."""
    path = Path(path)
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        raise FixtureError("no pude leer el fixture %s: %s" % (path, exc))
    for key in REQUIRED_FIXTURE_KEYS:
        if key not in data:
            raise FixtureError("el fixture %s no declara `%s`" % (path, key))
    if data["family"] not in FAMILIES:
        raise FixtureError("familia desconocida: %s (conocidas: %s)"
                           % (data["family"], ", ".join(FAMILIES)))
    if not isinstance(data["tasks"], list) or not data["tasks"]:
        raise FixtureError("el fixture %s no tiene tareas" % path)
    for i, task in enumerate(data["tasks"]):
        if "id" not in task:
            raise FixtureError("la tarea %d del fixture no tiene `id`" % i)
    data["path"] = str(path)
    data.setdefault("learning_tasks", 0)
    data.setdefault("cwd", str(path.parent))
    return data


def ordered_tasks(fixture, seed):
    """Orden fijo por seed, **idéntico en todas las filas** (mitigación §5).

    No se usa `random`: el orden tiene que ser el mismo en otra máquina y en otro mes.
    Una rotación determinista por seed alcanza y se puede reproducir a mano.

    Un fixture puede declarar `fixed_order` y quedarse fuera de la rotación. La familia C
    lo necesita: su protocolo es **aprender en el repo A y medir en el B**, y rotar el
    orden mete tareas del repo B en la fase de aprendizaje, que es exactamente la
    exposición previa que el protocolo prohíbe.
    """
    tasks = list(fixture["tasks"])
    if not seed or fixture.get("fixed_order"):
        return tasks
    corrimiento = int(seed) % len(tasks) if str(seed).lstrip("-").isdigit() else (
        sum(ord(c) for c in str(seed)) % len(tasks))
    return tasks[corrimiento:] + tasks[:corrimiento]


def matrix(fixture, *, rows=ROWS, repeats=3, seed=None):
    """La grilla completa: familia × fila × repetición × tarea, en orden fijo."""
    for row in rows:
        if row in BLOCKED_ROWS:
            raise ValueError(BLOCKED_ROWS[row])
    celdas = []
    for row in rows:
        for repeticion in range(1, repeats + 1):
            for indice, task in enumerate(ordered_tasks(fixture, seed)):
                celdas.append({
                    "family": fixture["family"], "fixture": fixture["name"], "row": row,
                    "repeat": repeticion, "task": task["id"], "task_index": indice,
                    "phase": "learning" if indice < fixture["learning_tasks"] else "measure",
                })
    return celdas


# ------------------------------------------------------------------------ ejecución
IGNORAR = shutil.ignore_patterns("__pycache__", "*.pyc", ".git", "celdas")


def prepare_workdir(fixture, destino) -> str:
    """Copia limpia del fixture para **una** celda.

    Sin esto, la celda que corre segunda hereda el fix de la primera y el gate sale 0 sin
    que el agente haya hecho nada: la medición deja de medir. Cada celda arranca del
    mismo estado o el experimento no existe.
    """
    destino = Path(destino)
    if destino.exists():
        shutil.rmtree(destino)
    destino.parent.mkdir(parents=True, exist_ok=True)
    shutil.copytree(fixture["cwd"], destino, ignore=IGNORAR)
    return str(destino)


def _run(command, *, cwd, timeout, env=None):
    try:
        out = subprocess.run(command, cwd=cwd, capture_output=True, text=True,
                             timeout=timeout, env=env)
        return out.returncode, out.stdout, out.stderr
    except subprocess.TimeoutExpired:
        return None, "", "timeout tras %ss" % timeout
    except OSError as exc:
        return None, "", str(exc)


METRICS_RE = re.compile(r"^NIGHTSHIFT_BENCH\s+(\{.*\})\s*$", re.M)


def run_cell(cell, fixture, *, agent_command, timeout, env=None, cwd=None,
             placeholders=None):
    """Prepara, corre el agente, corre el gate. Devuelve un registro, nunca levanta.

    El criterio de resolución es el del pre-registro: **el gate del fixture sale 0 y
    salía ≠ 0 antes**. No hay juicio de modelo en ningún punto de esta función.

    Las métricas del agente son opcionales: si el comando imprime una línea
    `NIGHTSHIFT_BENCH {"tool_calls": N}` se registran, y si no, quedan en `null` y el
    reporte lo dice. Contar tool calls es cosa del harness, no de nightshift, y
    estimarlas sería inventar un dato.
    """
    cwd = cwd or fixture["cwd"]
    task = next(t for t in fixture["tasks"] if t["id"] == cell["task"])
    registro = dict(cell)
    registro.update({"started_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                     "tool_calls": None, "error": None})
    inicio = time.time()

    if task.get("setup"):
        code, _, err = _run(task["setup"], cwd=cwd, timeout=timeout, env=env)
        if code != 0:
            registro.update({"resolved": None, "error": "setup falló: %s" % err.strip()[:200],
                             "seconds": round(time.time() - inicio, 2)})
            return registro

    code_antes, _, _ = _run(fixture["gate"], cwd=cwd, timeout=timeout, env=env)
    registro["gate_before"] = code_antes

    # `{agentes}` y `{root}` son absolutos a propósito: la celda corre en una copia bajo
    # el directorio de la corrida, no dentro del fixture, así que cualquier ruta relativa
    # al fixture apunta a otro lado. La documentación decía `../../agentes/` y era falsa.
    sustituciones = dict(placeholders or {})
    sustituciones.update({"{prompt}": task.get("prompt", ""), "{task}": task["id"],
                          "{row}": cell["row"], "{workdir}": str(cwd)})
    command = []
    for part in agent_command:
        for clave, valor in sustituciones.items():
            part = part.replace(clave, str(valor))
        command.append(part)
    code_agente, salida, err = _run(command, cwd=cwd, timeout=timeout, env=env)
    registro["agent_exit"] = code_agente
    match = METRICS_RE.search(salida or "")
    if match:
        try:
            metricas = json.loads(match.group(1))
            registro["tool_calls"] = metricas.get("tool_calls")
        except ValueError:
            pass
    if code_agente is None:
        registro["error"] = "el agente no terminó: %s" % err.strip()[:200]

    code_despues, _, _ = _run(fixture["gate"], cwd=cwd, timeout=timeout, env=env)
    registro["gate_after"] = code_despues
    registro["resolved"] = bool(code_antes not in (0, None) and code_despues == 0)

    # Familia D: la proporción de memoria falsa o stale la calcula un **script
    # determinista del fixture** contra un ground truth hecho a mano, no un modelo
    # (PREREG §3-D). nightshift corre el script y anota lo que diga; no clasifica.
    if fixture.get("classify"):
        code_clasif, salida_clasif, err_clasif = _run(fixture["classify"], cwd=cwd,
                                                      timeout=timeout, env=env)
        match = METRICS_RE.search(salida_clasif or "")
        if code_clasif == 0 and match:
            try:
                registro["false_stale_ratio"] = float(
                    json.loads(match.group(1))["false_stale_ratio"])
            except (ValueError, KeyError, TypeError):
                registro["error"] = "el clasificador no devolvió `false_stale_ratio`"
        else:
            registro["error"] = ("el clasificador falló: %s"
                                 % (err_clasif or "").strip()[:160]) or registro["error"]

    registro["seconds"] = round(time.time() - inicio, 2)
    return registro


# ------------------------------------------------------------- validar un fixture
def check_fixture(fixture, *, timeout=120, log=None) -> dict:
    """Afirma que cada tarea del fixture **es una tarea**.

    Dos maneras de que un fixture no mida nada, y las dos son silenciosas:

    - una tarea que **ya pasa** antes de que el agente toque nada — el gate sale 0 en el
      estado inicial y la celda cuenta como resuelta sin trabajo;
    - una tarea que **no se puede resolver** — ninguna resolución es posible y la celda
      cuenta como fallo para todas las filas por igual.

    Se comprueban las dos aplicando el fix de referencia sobre una copia limpia. El fix
    de referencia existe para esto y nada más: nunca se le muestra al agente.
    """
    say = log or (lambda _m: None)
    resultados = []
    referencia = fixture.get("reference_fix")
    import tempfile

    for task in fixture["tasks"]:
        entorno = dict(os.environ)
        entorno["NIGHTSHIFT_BENCH_TASK"] = task["id"]
        # Un fixture con varios repos necesita un fix por tarea, no uno solo.
        referencia = task.get("reference_fix") or fixture.get("reference_fix")
        with tempfile.TemporaryDirectory(prefix="nightshift-fixcheck-") as tmp:
            trabajo = prepare_workdir(fixture, Path(tmp) / "repo")
            antes, _, _ = _run(fixture["gate"], cwd=trabajo, timeout=timeout, env=entorno)
            despues = None
            if referencia:
                origen, destino = referencia["apply"]
                shutil.copyfile(Path(trabajo) / origen, Path(trabajo) / destino)
                despues, _, _ = _run(fixture["gate"], cwd=trabajo, timeout=timeout,
                                     env=entorno)
        problemas = []
        if antes == 0:
            problemas.append("el gate ya sale 0 sin tocar nada: no es una tarea")
        if antes is None:
            problemas.append("el gate no terminó en el estado inicial")
        if referencia and despues != 0:
            problemas.append("el fix de referencia no la resuelve (gate salió %s)" % despues)
        if not referencia:
            problemas.append("el fixture no declara `reference_fix`: no se puede afirmar "
                             "que la tarea sea resoluble")
        resultados.append({"task": task["id"], "gate_before": antes, "gate_after": despues,
                           "problems": problemas})
        say("  %-20s antes=%s después=%s %s"
            % (task["id"], antes, despues, "OK" if not problemas else "; ".join(problemas)))
    return {"fixture": fixture["name"], "family": fixture["family"],
            "tasks": resultados,
            "ok": all(not r["problems"] for r in resultados)}


# ------------------------------------------------------------------------- resumen
def median(values):
    values = sorted(v for v in values if v is not None)
    if not values:
        return None
    mitad = len(values) // 2
    if len(values) % 2:
        return float(values[mitad])
    return (values[mitad - 1] + values[mitad]) / 2.0


def summarize(records) -> dict:
    """Mediana y rango por celda. Cada repetición es una corrida, y se reportan todas."""
    resumen = {}
    for record in records:
        if record.get("phase") == "learning":
            continue
        clave = (record["family"], record["row"])
        celda = resumen.setdefault(clave, {"repeats": {}, "n": 0})
        repeticion = celda["repeats"].setdefault(record["repeat"],
                                                 {"resolved": [], "tool_calls": [],
                                                  "false_stale": []})
        celda["n"] += 1
        if record.get("resolved") is not None:
            repeticion["resolved"].append(1.0 if record["resolved"] else 0.0)
        if record.get("tool_calls") is not None:
            repeticion["tool_calls"].append(float(record["tool_calls"]))
        if record.get("false_stale_ratio") is not None:
            repeticion["false_stale"].append(float(record["false_stale_ratio"]))

    salida = {}
    for (family, row), celda in resumen.items():
        tasas, calls, falsas = [], [], []
        for repeticion in celda["repeats"].values():
            if repeticion["resolved"]:
                tasas.append(sum(repeticion["resolved"]) / len(repeticion["resolved"]))
            calls.extend(repeticion["tool_calls"])
            if repeticion["false_stale"]:
                falsas.append(sum(repeticion["false_stale"]) / len(repeticion["false_stale"]))
        salida[(family, row)] = {
            "family": family, "row": row, "runs": len(celda["repeats"]), "n": celda["n"],
            "resolution_rate": median(tasas),
            "resolution_rate_range": [min(tasas), max(tasas)] if tasas else None,
            "tool_calls_median": median(calls),
            "false_stale_ratio": median(falsas),
            "false_stale_range": [min(falsas), max(falsas)] if falsas else None,
        }
    return salida


def decide(summary, prereg) -> dict:
    """La regla de §1, tal cual está escrita. `go = None` si falta un umbral.

    Indecidible no es no-go, y sobre todo no es go. Un runner que redondea "no sé" a
    "sí" es la forma más cara de equivocarse que tiene este proyecto.
    """
    por_familia = {}
    for family in FAMILIES:
        fila = primary_threshold(prereg, family)
        umbral = fila["threshold"] if fila else None
        spec = PRIMARY[family]
        s0 = (summary.get((family, "S0")) or {}).get(spec["metric"])
        s1 = (summary.get((family, "S1")) or {}).get(spec["metric"])
        cumple = umbral.met(s0, s1, better=spec["better"]) if umbral else None
        por_familia[family] = {"metric": spec["metric"], "label": spec["label"],
                               "better": spec["better"], "S0": s0, "S1": s1,
                               "threshold": fila["raw"] if fila else None,
                               "met": cumple}
    faltantes = [f for f, item in por_familia.items() if item["met"] is None]
    alcanzadas = [f for f, item in por_familia.items() if item["met"] is True]
    go = None if faltantes else (len(alcanzadas) >= 2)
    return {"por_familia": por_familia, "familias_alcanzadas": alcanzadas,
            "indecidibles": faltantes, "go": go,
            "regla": "go si y sólo si mejora ≥ umbral en ≥2 de A/C/D y cero regresión "
                     "frente a S0 (PREREG §1). La tolerancia de regresión es un "
                     "TODO(Matias): mientras no esté, esta parte de la regla no se "
                     "puede evaluar."}
