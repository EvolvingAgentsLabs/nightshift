---
description: Run nightshift dream phase 1 (consolidate) over closed trajectories using the local Qwen model. Use when the user asks to consolidate, to run dream, or why nothing reaches candidate.
disable-model-invocation: true
---

# /nightshift:dream

Fase 1 de dream — `consolidate`. **La fase 2 (`verify`) no existe:** es M5 y está
bloqueada hasta el veredicto de M4, así que nada llega a `procedure`.

Corré el CLI y reportá su salida:

```sh
nightshift dream
```

Si `nightshift` no está en el `PATH`, usá `"${CLAUDE_PLUGIN_ROOT}/bin/nightshift" dream`.

Argumentos útiles, si el usuario los pide:

- `--dry-run` — muestra qué haría sin escribir nada.
- `--lookback-days N` — período a consolidar (7 por defecto).
- `--model "<comando>"` — modelo local explícito, en vez de la autodetección.
- `--selftest` — el gate de M3-a: corre sobre un set fixture en un store desechable.

Después resumí en dos o tres líneas:

- cuántos grupos se consolidaron y cuántas trayectorias quedaron en `candidate`,
- qué contradicciones se enlazaron (la vieja queda `superseded`, **no** borrada), y
- el caveat honesto: una `candidate` no está verificada. Se inyecta con menos peso y
  marcada como no verificada, y así hay que tratarla.

Códigos de salida, porque distinguen tres cosas distintas:

- `0` — consolidó; o no había nada que consolidar; o el modelo dijo que las
  trayectorias del período no comparten patrón. Las tres son noches normales.
- `1` — el modelo produjo algo que no se pudo persistir (fuga, ruta en el patrón, JSON
  roto). Eso sí es que dream no consolidó, y hay que ir a mirar.
- `2` — no hay modelo local. dream **no** cae a una API remota ni a una heurística.
  Si pasa esto, decíselo al usuario tal cual: falta un modelo Qwen local (ollama), no es
  un bug de nightshift.
