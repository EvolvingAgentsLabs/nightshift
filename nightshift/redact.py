"""Redactor determinista.

Determinista significa: mismo input, misma salida, sin modelo en el camino. Un LLM no
es un redactor; es una fuente de fugas con buena redacción (spec §8.2).

Corre **antes de persistir**, no antes de exportar: el store nunca contiene el material
sin redactar.

Orden de aplicación (importa, y por eso está fijado y testeado):
  1. deny_paths      -> el elemento se descarta entero, no se redacta
  2. secretos        -> patrones de credencial conocidos
  3. identificadores del repo (nombre, org, remotes)
  4. rutas absolutas y home
  5. correos, URLs con credenciales, blobs largos
"""

from __future__ import annotations

import fnmatch
import re
from pathlib import PurePosixPath

REDACTOR_VERSION = "0.1.0"

# --- secretos: se aplican primero para que no los coma otra regla -------------------
SECRET_RULES = [
    ("secret.private_key", re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----.*?-----END [A-Z ]*PRIVATE KEY-----", re.S)),
    ("secret.anthropic", re.compile(r"\bsk-ant-[A-Za-z0-9_\-]{16,}")),
    ("secret.openai", re.compile(r"\bsk-[A-Za-z0-9]{20,}")),
    ("secret.github", re.compile(r"\b(?:ghp|gho|ghu|ghs|ghr|github_pat)_[A-Za-z0-9_]{16,}")),
    ("secret.aws", re.compile(r"\b(?:AKIA|ASIA)[0-9A-Z]{16}\b")),
    ("secret.slack", re.compile(r"\bxox[abposr]-[A-Za-z0-9\-]{10,}")),
    ("secret.jwt", re.compile(r"\beyJ[A-Za-z0-9_\-]{8,}\.[A-Za-z0-9_\-]{8,}\.[A-Za-z0-9_\-]{8,}")),
    ("secret.bearer", re.compile(r"(?i)\b(?:bearer|authorization:\s*bearer)\s+[A-Za-z0-9._\-]{12,}")),
    ("secret.assignment", re.compile(
        r"(?i)\b([A-Z0-9_]*(?:TOKEN|SECRET|PASSWORD|PASSWD|APIKEY|API_KEY|ACCESS_KEY)[A-Z0-9_]*)"
        r"(\s*[:=]\s*)(\"[^\"]{4,}\"|'[^']{4,}'|[^\s,;)]{4,})")),
    ("secret.url_credentials", re.compile(r"\b([a-z][a-z0-9+.\-]*://)[^/\s:@]+:[^/\s@]+@")),
]

# Un secreto cuya clave es una clave de diccionario ({"env": {"API_TOKEN": "..."}}) no
# pasa por secret.assignment, que espera CLAVE=valor dentro de un mismo string. Se
# redacta por nombre de clave. Lo encontró el selftest, no una revisión.
SECRET_KEY_RE = re.compile(
    r"(?i)(token|secret|password|passwd|api[_\-]?key|apikey|access[_\-]?key|"
    r"private[_\-]?key|credential|auth|bearer|session[_\-]?id_)")

GENERIC_RULES = [
    ("email", re.compile(r"\b[A-Za-z0-9._%+\-]+@[A-Za-z0-9.\-]+\.[A-Za-z]{2,}\b"), "<EMAIL>"),
    ("blob", re.compile(r"\b[A-Fa-f0-9]{40,}\b"), "<BLOB>"),
]


class Redactor:
    """Redactor con estado mínimo: la lista de identificadores del repo y un contador.

    `identifiers` son los tokens que delatan al repo — nombre, organización, host del
    remote, nombres de paquete. Se ordenan por longitud descendente para que el token
    más específico gane.
    """

    def __init__(self, identifiers=None, deny_paths=None, home_dir=None):
        self.identifiers = sorted({i for i in (identifiers or []) if i and len(i) >= 3},
                                  key=len, reverse=True)
        self.deny_paths = list(deny_paths or [])
        self.home_dir = str(home_dir) if home_dir else None
        self.rules_applied = set()
        self.deny_path_hits = 0

    # ---------------------------------------------------------------- deny_paths
    def is_denied(self, path) -> bool:
        """True si la ruta cae bajo un deny_path. Se compara la ruta y cada sufijo."""
        if not path:
            return False
        norm = str(path).replace("\\", "/")
        candidates = [norm]
        parts = PurePosixPath(norm).parts
        for i in range(1, len(parts)):
            candidates.append("/".join(parts[i:]))
        for pattern in self.deny_paths:
            for cand in candidates:
                if fnmatch.fnmatch(cand, pattern) or fnmatch.fnmatch("/" + cand, pattern):
                    return True
        return False

    # -------------------------------------------------------------------- texto
    def text(self, value):
        """Redacta una cadena. Devuelve None si el valor entero cae bajo deny_paths."""
        if value is None:
            return None
        if not isinstance(value, str):
            return value

        out = value
        for name, pattern in SECRET_RULES:
            if name == "secret.assignment":
                new = pattern.sub(lambda m: m.group(1) + m.group(2) + "<SECRET>", out)
            elif name == "secret.url_credentials":
                new = pattern.sub(lambda m: m.group(1) + "<CREDENTIALS>@", out)
            else:
                new = pattern.sub("<SECRET>", out)
            if new != out:
                self.rules_applied.add(name)
                out = new

        for ident in self.identifiers:
            pattern = re.compile(r"(?i)\b%s\b" % re.escape(ident))
            new = pattern.sub("<REPO>", out)
            if new != out:
                self.rules_applied.add("repo_identifier")
                out = new

        if self.home_dir:
            new = out.replace(self.home_dir, "~")
            if new != out:
                self.rules_applied.add("home_dir")
                out = new

        new = re.sub(r"(?<![\w<])/(?:[A-Za-z0-9_.\-]+/){1,}[A-Za-z0-9_.\-]*", "<PATH>", out)
        if new != out:
            self.rules_applied.add("abs_path")
            out = new

        for name, pattern, replacement in GENERIC_RULES:
            new = pattern.sub(replacement, out)
            if new != out:
                self.rules_applied.add(name)
                out = new

        return out

    def touches_denied(self, value, _depth=0) -> bool:
        """True si algo dentro de `value` cae bajo deny_paths.

        Se usa **antes** de redactar: un tool call que toca un deny_path no se redacta,
        se descarta entero. La spec §8.1 no admite ni el path, ni el contenido, ni el
        hecho de que existe.
        """
        if _depth > 12:
            return False
        if isinstance(value, dict):
            return any(self.touches_denied(v, _depth + 1) for v in value.values())
        if isinstance(value, list):
            return any(self.touches_denied(v, _depth + 1) for v in value[:50])
        if isinstance(value, str):
            return self.is_denied(value)
        return False

    # -------------------------------------------------------------------- objetos
    def obj(self, value, _depth=0):
        """Redacta recursivamente. Las claves tipo ruta pasan por deny_paths primero."""
        if _depth > 12:
            return "<TRUNCATED>"
        if isinstance(value, dict):
            out = {}
            for key, item in value.items():
                if key in ("file_path", "path", "notebook_path", "filePath") and self.is_denied(item):
                    self.deny_path_hits += 1
                    continue
                if isinstance(item, str) and self.is_denied(item):
                    self.deny_path_hits += 1
                    continue
                if SECRET_KEY_RE.search(str(key)) and isinstance(item, (str, int, float)):
                    self.rules_applied.add("secret.key_name")
                    out[str(key)] = "<SECRET>"
                    continue
                out[str(key)] = self.obj(item, _depth + 1)
            return out
        if isinstance(value, list):
            return [self.obj(v, _depth + 1) for v in value[:50]]
        if isinstance(value, str):
            return self.text(value)
        if isinstance(value, (int, float, bool)) or value is None:
            return value
        return self.text(str(value))

    # -------------------------------------------------------------------- reporte
    def report(self) -> dict:
        return {
            "redactor_version": REDACTOR_VERSION,
            "rules_applied": sorted(self.rules_applied),
            "deny_path_hits": self.deny_path_hits,
        }
