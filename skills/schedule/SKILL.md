---
description: Inspect or set up nightshift's nightly dream run (launchd, systemd user timer, or foreground loop). Use when the user asks about scheduling, the nightly run, or whether dream ran last night.
disable-model-invocation: true
---

# /nightshift:schedule

Scheduler de la corrida nocturna (M3-b). Por defecto **reporta**, no instala.

```sh
nightshift schedule status
```

Si `nightshift` no está en el `PATH`, usá `"${CLAUDE_PLUGIN_ROOT}/bin/nightshift" schedule status`.

Resumí en dos o tres líneas: qué backend está elegido, si hay algo instalado, y **las
últimas corridas con su resultado** — que es lo que hace verificable el gate de M3 (tres
noches seguidas sin intervención). Si no hay corridas registradas, decilo: un scheduler
sin corridas es una promesa, no un hecho.

Instalar toca el gestor de arranque del usuario, así que **no lo hagas sin que te lo
pidan**. Cuando te lo pidan:

```sh
nightshift schedule install --dry-run    # mostrar la unidad, no escribir nada
nightshift schedule install              # escribir y activar
nightshift schedule uninstall            # sacarla
```

Backends: `launchd` (macOS), `systemd` (timer de **usuario**), `loop` (primer plano, para
desarrollo: `nightshift schedule loop`). `--backend` los fuerza; sin él, autodetección.

Códigos de salida de `status`: `0` si hay un timer instalado, `1` si no.
