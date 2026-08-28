---
description: Run a nightshift sleep cycle on demand — seal the current chapter and consolidate it without ending the session. Use when the user asks to dream now, to consolidate what was just done, or to close a chapter.
disable-model-invocation: true
---

# /nightshift:sleep

Un ciclo de sueño **a demanda**, sin cerrar la sesión.

Dream sólo ve trayectorias `closed`, y la de la sesión en curso se cierra en `SessionEnd`.
Es decir: para soñar sobre lo que acabás de hacer había que dejar de hacerlo. Esto pone el
borde donde lo pone la persona que trabaja — un `make check` en verde, un merge — en vez
de esperar a que la sesión termine.

Corré el CLI y reportá su salida:

```sh
nightshift sleep
```

Si `nightshift` no está en el `PATH`, usá `"${CLAUDE_PLUGIN_ROOT}/bin/nightshift" sleep`.

Qué hace, en orden:

1. Busca el capítulo abierto **de este repo**. El CLI no recibe el `session_id`, así que
   lo identifica por repo y actividad; si hay más de uno abierto se niega y pide
   `--trajectory <id>`, porque sellarle el capítulo a la sesión equivocada la parte al
   medio sin que se entere.
2. Lo sella: `closed`, con el desenlace que infiere la misma regla que usa `SessionEnd`.
   **La sesión sigue capturando** — el próximo evento de hook abre la trayectoria
   siguiente.
3. Consolida **sólo el grupo de ese capítulo**. Es `dream` y nada más: mismo modelo,
   mismos gates, misma validación. Dormir sobre lo que acabás de hacer no es consolidar la
   semana entera, y con el backend `claude-code` la diferencia se paga por token.

Argumentos útiles, si el usuario los pide:

- `--dry-run` — decir qué capítulo sellaría, sin sellar y sin preguntarle nada al modelo.
- `--trajectory <id>` — cuál sellar, cuando hay más de uno abierto.
- `--verbose` — el progreso por grupo.

## Qué no hace

- **No verifica nada.** Lo que sale es `candidate`, igual que en la corrida nocturna: la
  fase 2 (`verify`) es M5 y no existe, así que nada llega a `procedure`.
- **No reemplaza la corrida nocturna.** `nightshift dream` sigue consolidando el período
  entero; esto es un capítulo.
- **No sella una silueta.** Si el capítulo tiene pasos y ninguno con contenido, se niega y
  sale 1: eso es un problema de captura, y lo diagnostica `nightshift doctor`.
