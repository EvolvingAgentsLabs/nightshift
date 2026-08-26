"""Configuración y rutas.

Dos invariantes de este módulo, ambos testeados:

1. `deny_paths` es obligatorio antes de capturar (spec §8.1). Sin archivo de config
   resuelto, `is_enabled()` es False y no se captura nada.
2. nightshift nunca escribe bajo el árbol de Auto Memory (spec §1.3.4). `guard_path()`
   levanta si alguien lo intenta, y es el único camino a disco del paquete.
3. El store vive en un solo lugar, lo ejecute quien lo ejecute. Ver `home()`.
"""

from __future__ import annotations

import json
import os
import re
from pathlib import Path

CONFIG_FILENAME = "config.json"

# Rutas propiedad de la memoria declarativa nativa. nightshift lee MEMORY.md como
# señal de retrieval y no escribe nada acá. Ver ADR-001.
AUTO_MEMORY_RE = re.compile(r"/\.claude/projects/[^/]+/memory(/|$)")

DEFAULT_DENY_PATHS = [
    "**/.env",
    "**/.env.*",
    "**/*.pem",
    "**/*.key",
    "**/*.p12",
    "**/id_rsa*",
    "**/id_ed25519*",
    "**/.ssh/**",
    "**/.aws/**",
    "**/.gnupg/**",
    "**/credentials*",
    "**/secrets/**",
    "**/*.sqlite",
    "**/.claude/**",
    "**/.git/config",
]

DEFAULTS = {
    "enabled": True,
    "deny_paths": DEFAULT_DENY_PATHS,
    "max_injected": 3,
    "max_steps_per_trajectory": 400,
    "max_result_summary_chars": 400,
    "retrieval_lookback_days": 30,
    # Una sesión que murió sin `SessionEnd` deja su trayectoria `open` para siempre, y el
    # retrieval sólo mira `closed`/`candidate`/`procedure`: se pierde entera. Se cierra
    # por falta de actividad, no por antigüedad — una sesión larga sigue viva.
    "orphan_after_hours": 12,
    # Dream (M3). `model_command` en null significa autodetectar: ollama en el PATH y un
    # modelo qwen ya descargado, el más chico. Nunca se descarga nada solo.
    "model_command": None,
    "dream_lookback_days": 7,
    "dream_timeout_seconds": 180,
    # Scheduler (M3-b). `auto` detecta: launchd en macOS, systemd de usuario en Linux,
    # `loop` en cualquier otra cosa. La ventana nocturna asume portátil enchufado.
    "scheduler_backend": "auto",
    "dream_hour": 3,
    "dream_minute": 30,
    "loop_interval_minutes": 360,
    # Transferencia cross-repo real necesita `abstraction`, que la produce dream (M3).
    # Hasta entonces esto inyecta trayectorias crudas de otro repo: apagado por defecto.
    "cross_repo": False,
}


DEFAULT_HOME = "~/.nightshift"


def home() -> Path:
    """Directorio de datos de nightshift. Uno solo, en todos los contextos.

    `NIGHTSHIFT_HOME` (para tests y para quien quiera moverlo) o `~/.nightshift`.

    **`CLAUDE_PLUGIN_DATA` se ignora a propósito.** Claude Code se lo pasa a los hooks
    pero no al Bash tool, así que usarlo partía el store en dos: los hooks escribían en
    `~/.claude/plugins/data/<id>/` y `nightshift init` configuraba `~/.nightshift`. El
    resultado era una captura que nunca arrancaba y un `status` que siempre decía cero.
    Una ruta que cambia según quién ejecuta el proceso no es una ruta.
    """
    value = os.environ.get("NIGHTSHIFT_HOME")
    if value:
        return Path(value).expanduser()
    return Path(DEFAULT_HOME).expanduser()


def config_path() -> Path:
    return home() / CONFIG_FILENAME


def db_path() -> Path:
    return guard_path(home() / "trajectories.sqlite3")


def log_path() -> Path:
    return guard_path(home() / "nightshift.log")


def guard_path(path: Path) -> Path:
    """Única puerta a disco del paquete. Levanta si la ruta es de Auto Memory."""
    resolved = str(Path(path).expanduser())
    if AUTO_MEMORY_RE.search(resolved.replace("\\", "/")):
        raise PermissionError(
            "nightshift nunca escribe en el arbol de Auto Memory (spec 1.3.4): %s" % resolved
        )
    return Path(resolved)


def load() -> dict:
    """Config efectiva. Sin archivo, devuelve los defaults marcados como no configurado."""
    cfg = dict(DEFAULTS)
    cfg["configured"] = False
    path = config_path()
    try:
        if path.is_file():
            user = json.loads(path.read_text(encoding="utf-8"))
            if isinstance(user, dict):
                cfg.update({k: v for k, v in user.items() if k in DEFAULTS})
                cfg["configured"] = True
    except (OSError, ValueError):
        # Config ilegible: se degrada a no configurado. Nunca levanta hacia el hook.
        pass
    return cfg


def is_enabled() -> bool:
    """Capturar exige config explícita con deny_paths resuelto (spec §8.1)."""
    cfg = load()
    return bool(cfg["configured"] and cfg["enabled"] and cfg["deny_paths"])


def init(force: bool = False) -> Path:
    """Escribe la config inicial con los deny_paths por defecto."""
    path = guard_path(config_path())
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists() and not force:
        return path
    payload = {k: DEFAULTS[k] for k in DEFAULTS}
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return path
