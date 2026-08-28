"""Señales del repo y clasificación estructural de la tarea.

Todo lo de acá es determinista y sin modelo: el retrieval de `SessionStart` se hace
"por estructura" (plan §2), y una clasificación que dependa de un LLM no es
reproducible ni auditable.
"""

from __future__ import annotations

import hashlib
import re
import subprocess
from pathlib import Path

# Orden fijo: gana la primera que matchea. Cambiar el orden cambia los datos, así que
# está testeado.
TASK_TYPE_RULES = [
    ("debug_test_failure", re.compile(
        r"(?i)\b(tests?|pytest|jest|vitest|unittest|falla\w*|fail\w*|traceback|assert\w*|"
        r"stack ?trace|romp\w*|broke\w*)\b")),
    ("debug_runtime", re.compile(
        r"(?i)\b(crash\w*|cuelga|hang\w*|deadlock|timeout|leak\w*|segfault|oom|panic|"
        r"excepci[o\u00f3]n|exception|error\w*|bug\w*)\b")),
    ("refactor", re.compile(
        r"(?i)\b(refactor\w*|simplific\w*|renombr\w*|rename|limpi\w*|cleanup|dedup\w*)\b")),
    ("implement_feature", re.compile(
        r"(?i)\b(implement\w*|agrega\w*|a[\u00f1n]ad\w*|add|crea\w*|create|build|"
        r"escrib\w*|write)\b")),
    ("docs", re.compile(r"(?i)\b(docs?|documenta\w*|readme|spec|adr|changelog)\b")),
    ("explore", re.compile(
        r"(?i)\b(explica\w*|explain|entend\w*|understand|c[o\u00f3]mo funciona|how does|"
        r"d[o\u00f3]nde|where is|revis\w*|review|analiz\w*|analyz\w*|analys\w*|"
        r"audit\w*|inspeccion\w*|inspect\w*|diagnostic\w*|c[o\u00f3]mo (?:est[a\u00e1]|va|"
        r"anda|viene)\w*)\b")),
]
DEFAULT_TASK_TYPE = "general"

TOOL_MAP = {
    "Read": "read_file",
    "NotebookRead": "read_file",
    "Edit": "edit_file",
    "NotebookEdit": "edit_file",
    "MultiEdit": "edit_file",
    "Write": "write_file",
    "Bash": "run_shell",
    "BashOutput": "run_shell",
    "Grep": "search",
    "Glob": "search",
    "WebFetch": "fetch",
    "WebSearch": "fetch",
}

CORRECTION_RE = re.compile(
    r"(?i)(\bno,\s|\bno\b.{0,12}\b(est[aá]|es)\b.{0,10}\b(mal|incorrect)|"
    r"\bincorrecto\b|\beso est[aá] mal\b|\bthat'?s wrong\b|\bthat is wrong\b|"
    r"\bnot (right|correct)\b|\bwrong\b|\brevert\b|\bundo\b|\bdeshac|\bvolv[ée] atr[aá]s\b|"
    r"\bno es (as[ií]|eso)\b|\bactually,? no\b)")

# Un comando de test, y **en posición de comando**: al principio, o después de `;`,
# `&&`, `||`, `|`, un salto de línea o un `$(`. No en cualquier parte de la cadena.
#
# Medido sobre una sesión real de 252 pasos: buscando la subcadena en cualquier lugar,
# el 41% de los pasos quedaba marcado como señal decisiva. Los comandos de shell de una
# sesión de trabajo son compuestos —`cp x y; python3 - <<PY ...; make check`— y alcanzaba
# con que la palabra apareciera adentro de un heredoc para que el paso entero contara como
# concluyente. Una señal que dispara en la mitad de los pasos no es una señal.
TEST_CMD_RE = re.compile(
    r"(?im)(?:^|[;&|]|\$\(|\n)\s*(?:sudo\s+|env\s+\S+=\S+\s+)*"
    r"(pytest|unittest|python[0-9.]*\s+-m\s+(?:unittest|pytest)|npm (?:run )?test|"
    r"yarn test|go test|cargo test|make (?:test|check)|tox|jest|vitest|rspec|mvn test|"
    r"gradle test)\b")


# Comandos que **leen** el repositorio en vez de ejercitarlo (plan §7, F2).
#
# La distinción no es cosmética y salió de un caso medido. La candidata `1f94f424`
# abstrajo un mecanismo que no existe, y no lo alucinó: levantó dos salidas de `grep`
# —un comentario que decía "sin bandera de por medio" y un docstring que decía "el comando
# está redactado, y eso no lo afecta"— y las trató como observaciones sobre el bug que se
# estaba arreglando. Eran comentarios sobre un diseño **viejo y ya cambiado**.
#
# Un fallo, un test, una corrección son evidencia de esta sesión. La salida de un `grep` es
# el repositorio hablando de sí mismo, y puede estar describiendo algo ajeno, viejo o ya
# revertido. Anclar a un paso no distingue las dos cosas: las dos son pasos reales.
#
# Se ancla al principio de la línea o después de un separador, igual que `TEST_CMD_RE` y
# por el mismo motivo: un `grep` adentro de un heredoc no vuelve lectura al comando entero.
READ_CMD_RE = re.compile(
    r"(?im)(?:^|[;&|]|\$\(|\n)\s*(?:sudo\s+)*"
    r"(grep|rg|ag|ack|cat|head|tail|less|more|find|fd|ls|tree|wc|file|stat|"
    r"sed\s+-n|awk|jq|column|sort|uniq|"
    r"git\s+(?:log|show|diff|blame|status|branch|remote))\b")

# Las herramientas nativas que sólo leen. Vienen normalizadas por `normalize_tool`.
READ_TOOLS = frozenset(("read_file", "search", "fetch"))


def normalize_tool(native: str | None) -> str:
    if not native:
        return "other"
    if native in TOOL_MAP:
        return TOOL_MAP[native]
    return "other"


def classify_task(text: str | None) -> str:
    if not text:
        return DEFAULT_TASK_TYPE
    for name, pattern in TASK_TYPE_RULES:
        if pattern.search(text):
            return name
    return DEFAULT_TASK_TYPE


def _git(cwd: str, *args) -> str | None:
    try:
        out = subprocess.run(["git", "-C", cwd, *args], capture_output=True, text=True,
                             timeout=2.0)
    except (OSError, subprocess.SubprocessError):
        return None
    if out.returncode != 0:
        return None
    value = out.stdout.strip()
    return value or None


def repo_root(cwd: str) -> str:
    return _git(cwd, "rev-parse", "--show-toplevel") or str(Path(cwd).resolve())


def base_commit(cwd: str) -> str | None:
    sha = _git(cwd, "rev-parse", "HEAD")
    if sha and re.fullmatch(r"[a-f0-9]{7,40}", sha):
        return sha
    return None


def repo_identifiers(cwd: str) -> list[str]:
    """Tokens que delatan al repo. Alimentan al redactor (spec §8.2)."""
    idents = set()
    root = repo_root(cwd)
    idents.add(Path(root).name)
    remote = _git(cwd, "config", "--get", "remote.origin.url")
    if remote:
        cleaned = re.sub(r"^[a-z]+://", "", remote)
        cleaned = re.sub(r"^[^@]+@", "", cleaned)
        cleaned = re.sub(r"\.git$", "", cleaned)
        for token in re.split(r"[/:]", cleaned):
            token = token.strip()
            if token and "." not in token:
                idents.add(token)
    return sorted(t for t in idents if len(t) >= 3)


def repo_fingerprint(cwd: str) -> str:
    """SHA-256 de un identificador estable. Nunca el nombre en claro (schema §repo_fingerprint)."""
    remote = _git(cwd, "config", "--get", "remote.origin.url")
    seed = remote or repo_root(cwd)
    seed = re.sub(r"\.git$", "", seed.strip())
    return hashlib.sha256(seed.encode("utf-8")).hexdigest()


def memory_signal(cwd: str) -> bool:
    """¿Hay memoria nativa para este proyecto?

    Se lee **sólo como señal de retrieval** (spec §1.3.4). No se abre el contenido acá y
    nunca se escribe. Devuelve si existe, nada más.
    """
    try:
        base = Path.home() / ".claude" / "projects"
        if not base.is_dir():
            return False
        slug = str(Path(repo_root(cwd)).resolve()).replace("/", "-")
        for entry in base.iterdir():
            if entry.name.endswith(slug) or slug.endswith(entry.name):
                return (entry / "memory" / "MEMORY.md").is_file()
    except OSError:
        return False
    return False
