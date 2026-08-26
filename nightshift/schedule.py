"""Scheduler pluggable (M3-b, spec §7.1).

Tres backends detrás de una interfaz: `launchd` (macOS, target primario), `systemd`
(timer de **usuario**, nunca unidad de sistema) y `loop` (foreground, para desarrollo y
para máquinas sin lo anterior). El backend sale de la config, con autodetección.

Dos cosas que este módulo hace y conviene no deshacer:

**Instalar y activar son pasos distintos.** Escribir la unidad es reversible y se puede
leer; cargarla en el gestor del sistema no. `--dry-run` muestra la unidad sin escribirla y
`--no-activate` la escribe sin cargarla. Los tests usan el segundo: un test que llama a
`launchctl` de verdad le deja un job instalado a quien lo corra.

**El gate del scheduler no es que el timer exista, es que las corridas se vean.** Un
scheduler sin registro de corridas es una promesa: hay un timer y nadie sabe si anoche
hizo algo. Por eso cada corrida de dream queda en la tabla `runs` y `schedule status` la
muestra con su código de salida.

El gate real de M3 no es de este módulo: son tres noches seguidas sin intervención en la
Air, y lo corre una persona. Acá está el comando que lo hace verificable.
"""

from __future__ import annotations

import getpass
import os
import platform
import shutil
import subprocess
import sys
from datetime import datetime, timedelta
from pathlib import Path

from . import config

LABEL = "com.evolvingagentslabs.nightshift.dream"
SERVICE_NAME = "nightshift-dream"
BACKENDS = ("launchd", "systemd", "loop")


def _binary() -> str:
    """El `nightshift` que el scheduler va a invocar.

    Se resuelve al script del repo, no al del `PATH` del shell interactivo: launchd y
    systemd corren con un entorno mínimo donde ese `PATH` no existe.
    """
    candidate = Path(__file__).resolve().parent.parent / "bin" / "nightshift"
    if candidate.is_file():
        return str(candidate)
    found = shutil.which("nightshift")
    return found or "%s -m nightshift" % sys.executable


def detect(cfg=None) -> str:
    """Backend por autodetección: lo que la plataforma realmente ofrece."""
    cfg = cfg or {}
    configured = cfg.get("scheduler_backend", "auto")
    if configured in BACKENDS:
        return configured
    if platform.system() == "Darwin" and shutil.which("launchctl"):
        return "launchd"
    if platform.system() == "Linux" and shutil.which("systemctl"):
        return "systemd"
    return "loop"


class Backend:
    name = "?"

    def __init__(self, cfg):
        self.cfg = cfg
        self.hour = int(cfg.get("dream_hour", 3))
        self.minute = int(cfg.get("dream_minute", 30))

    # --- lo que cada backend define ---------------------------------------------
    @property
    def unit_path(self) -> Path | None:
        return None

    def render(self) -> str:
        raise NotImplementedError

    def activate(self):
        return []

    def deactivate(self):
        return []

    # --- lo común -----------------------------------------------------------------
    def command(self) -> list[str]:
        """El comando de la corrida nocturna.

        `caffeinate -s` cuando existe: la ventana nocturna asume portátil enchufado, y un
        equipo que se duerme a mitad de la consolidación deja el trabajo sin terminar
        (spec §7.1).
        """
        parts = []
        caffeinate = shutil.which("caffeinate")
        if caffeinate:
            parts += [caffeinate, "-s"]
        parts += [_binary(), "dream", "--backend", self.name]
        return parts

    def installed(self) -> bool:
        return bool(self.unit_path and self.unit_path.is_file())

    def install(self, *, dry_run=False, activate=True):
        text = self.render()
        if dry_run:
            return {"backend": self.name, "path": str(self.unit_path), "unit": text,
                    "written": False, "activated": False}
        path = config.guard_path(self.unit_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")
        # launchd no crea el directorio de logs: si no existe, el job falla al arrancar y
        # no queda registro de por qué.
        config.guard_path(config.home() / "logs").mkdir(parents=True, exist_ok=True)
        activated, detail = (False, "no activado (--no-activate)")
        if activate:
            activated, detail = self._run_all(self.activate())
        return {"backend": self.name, "path": str(path), "unit": text, "written": True,
                "activated": activated, "detail": detail}

    def uninstall(self):
        activated, detail = self._run_all(self.deactivate())
        removed = False
        if self.unit_path and self.unit_path.is_file():
            config.guard_path(self.unit_path).unlink()
            removed = True
        return {"backend": self.name, "removed": removed, "detail": detail,
                "deactivated": activated}

    def _run_all(self, commands):
        detail = []
        ok = True
        for command in commands:
            try:
                out = subprocess.run(command, capture_output=True, text=True, timeout=30)
            except (OSError, subprocess.SubprocessError) as exc:
                ok = False
                detail.append("%s: %s" % (Path(command[0]).name, exc))
                continue
            if out.returncode != 0:
                ok = False
                detail.append("%s salió %d: %s" % (Path(command[0]).name, out.returncode,
                                                   (out.stderr or "").strip()[:200]))
        return (ok if commands else False), ("; ".join(detail) if detail else "ok")

    def describe(self) -> str:
        return "%02d:%02d, todos los días" % (self.hour, self.minute)


class LaunchdBackend(Backend):
    name = "launchd"

    @property
    def unit_path(self) -> Path:
        return Path.home() / "Library" / "LaunchAgents" / ("%s.plist" % LABEL)

    def render(self) -> str:
        args = "".join("\n        <string>%s</string>" % part for part in self.command())
        logs = config.home() / "logs"
        return (
            '<?xml version="1.0" encoding="UTF-8"?>\n'
            '<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN"'
            ' "http://www.apple.com/DTDs/PropertyList-1.0.dtd">\n'
            '<plist version="1.0">\n'
            '<dict>\n'
            '    <key>Label</key>\n'
            '    <string>%s</string>\n'
            '    <key>ProgramArguments</key>\n'
            '    <array>%s\n'
            '    </array>\n'
            '    <key>StartCalendarInterval</key>\n'
            '    <dict>\n'
            '        <key>Hour</key><integer>%d</integer>\n'
            '        <key>Minute</key><integer>%d</integer>\n'
            '    </dict>\n'
            '    <key>RunAtLoad</key>\n'
            '    <false/>\n'
            '    <key>StandardOutPath</key>\n'
            '    <string>%s/dream.out.log</string>\n'
            '    <key>StandardErrorPath</key>\n'
            '    <string>%s/dream.err.log</string>\n'
            '</dict>\n'
            '</plist>\n'
        ) % (LABEL, args, self.hour, self.minute, logs, logs)

    def next_run(self, now: datetime | None = None) -> datetime:
        """Próxima corrida, calculada desde el `StartCalendarInterval` del plist.

        No consulta `launchctl print`: su salida no tiene un formato versionado
        contra el cual valga confiar en parsear (doc/00-spec.md §5.4 — la misma
        lección de los hooks aplica acá). El plist es la fuente de verdad: es
        exactamente lo que carga launchd.
        """
        now = now or datetime.now()
        candidate = now.replace(hour=self.hour, minute=self.minute, second=0, microsecond=0)
        if candidate <= now:
            candidate += timedelta(days=1)
        return candidate

    def _domain(self) -> str:
        return "gui/%d" % os.getuid()

    def activate(self):
        launchctl = shutil.which("launchctl")
        if not launchctl:
            return []
        return [[launchctl, "bootout", self._domain(), str(self.unit_path)],
                [launchctl, "bootstrap", self._domain(), str(self.unit_path)]]

    def deactivate(self):
        launchctl = shutil.which("launchctl")
        if not launchctl:
            return []
        return [[launchctl, "bootout", self._domain(), str(self.unit_path)]]

    def _run_all(self, commands):
        # El primer `bootout` es para reinstalar sobre un job ya cargado: que falle es lo
        # normal la primera vez, y no es un error de instalación.
        if len(commands) == 2:
            super()._run_all(commands[:1])
            return super()._run_all(commands[1:])
        return super()._run_all(commands)


class SystemdBackend(Backend):
    name = "systemd"

    @property
    def unit_path(self) -> Path:
        return Path.home() / ".config" / "systemd" / "user" / ("%s.timer" % SERVICE_NAME)

    @property
    def service_path(self) -> Path:
        return Path.home() / ".config" / "systemd" / "user" / ("%s.service" % SERVICE_NAME)

    def render(self) -> str:
        return (
            "[Unit]\n"
            "Description=nightshift dream (consolidate)\n"
            "\n"
            "[Timer]\n"
            "OnCalendar=*-*-* %02d:%02d:00\n"
            "Persistent=true\n"
            "\n"
            "[Install]\n"
            "WantedBy=timers.target\n"
        ) % (self.hour, self.minute)

    def render_service(self) -> str:
        return (
            "[Unit]\n"
            "Description=nightshift dream (consolidate)\n"
            "\n"
            "[Service]\n"
            "Type=oneshot\n"
            "ExecStart=%s\n"
        ) % " ".join(self.command())

    def install(self, *, dry_run=False, activate=True):
        if not dry_run:
            path = config.guard_path(self.service_path)
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(self.render_service(), encoding="utf-8")
        result = super().install(dry_run=dry_run, activate=activate)
        result["service"] = self.render_service()
        return result

    def uninstall(self):
        result = super().uninstall()
        if self.service_path.is_file():
            config.guard_path(self.service_path).unlink()
        return result

    def activate(self):
        systemctl = shutil.which("systemctl")
        if not systemctl:
            return []
        # Timer de usuario, nunca unidad de sistema (spec §7.1).
        return [[systemctl, "--user", "daemon-reload"],
                [systemctl, "--user", "enable", "--now", "%s.timer" % SERVICE_NAME]]

    def deactivate(self):
        systemctl = shutil.which("systemctl")
        if not systemctl:
            return []
        return [[systemctl, "--user", "disable", "--now", "%s.timer" % SERVICE_NAME]]


class LoopBackend(Backend):
    """Foreground. No instala nada en el sistema: lo corre quien lo mira."""

    name = "loop"

    @property
    def unit_path(self) -> Path:
        return config.home() / "schedule-loop.json"

    def render(self) -> str:
        return ('{\n  "backend": "loop",\n  "interval_minutes": %d,\n'
                '  "command": %s\n}\n'
                % (int(self.cfg.get("loop_interval_minutes", 360)),
                   '"%s"' % " ".join(self.command())))

    def describe(self) -> str:
        return "cada %d minuto(s), en primer plano" % int(
            self.cfg.get("loop_interval_minutes", 360))


def backend(name, cfg) -> Backend:
    return {"launchd": LaunchdBackend, "systemd": SystemdBackend,
            "loop": LoopBackend}[name](cfg)


def resolve(name, cfg) -> Backend:
    """Backend pedido, o el que la plataforma ofrece si se pidió `auto`."""
    if not name or name == "auto":
        name = detect(cfg)
    if name not in BACKENDS:
        raise ValueError("backend desconocido: %s (conocidos: %s)"
                         % (name, ", ".join(BACKENDS)))
    return backend(name, cfg)


def environment() -> dict:
    """Lo que hace falta saber para explicar por qué se eligió un backend."""
    return {
        "platform": platform.system(),
        "user": getpass.getuser(),
        "launchctl": bool(shutil.which("launchctl")),
        "systemctl": bool(shutil.which("systemctl")),
        "caffeinate": bool(shutil.which("caffeinate")),
    }
