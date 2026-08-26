# nightshift — Spec v0.3

| Campo | Valor |
|---|---|
| Versión | 0.3 |
| Estado | Draft — M0 |
| Reemplaza | v0.2 |
| Fuente de alcance | `doc/PLAN-v0.3.md` |
| ADRs vinculados | ADR-001, ADR-002 |
| Revisión | 0.3.2 — enmendada por lo aprendido corriendo M1+M2 |

> **Nota de procedencia.** Este repositorio se creó en el commit de M0. La v0.2 existía
> como documento de trabajo fuera del repo y no se importó. Esta v0.3 reconstruye la
> estructura de v0.2 y le aplica los siete cambios de §1 del plan; las secciones marcadas
> _(sin cambio respecto a v0.2)_ son reconstrucción, no citas literales. El changelog de
> §12 registra exactamente qué cambió. Ver `LATER.md` §"Deuda de procedencia".

---

## 1. Producto

### 1.1 Positioning

nightshift es una **capa de memoria procedimental sobre la memoria declarativa nativa
del agente** ("procedural memory layer over the agent's native declarative memory").

Claude Code ya trae Auto Memory (notas declarativas por repositorio) y Auto Dream
(consolidación en background). nightshift **no reemplaza ni sustituye Auto Memory**.
Corre encima, coexiste, y aporta lo que la memoria declarativa no puede aportar por
diseño: la **trayectoria causal** que llevó a un fix, no el hecho resultante.

Formulación de una línea:

> Auto Memory recuerda *qué es verdad en este repo*. nightshift recuerda *cómo se
> averiguó*, y sólo lo asciende a procedimiento cuando reproducirlo pasa un gate.

Está prohibido en toda comunicación del proyecto (README, ADRs, commits, demos)
presentar nightshift como reemplazo, mejora o parche de Auto Memory. Si un texto
puede leerse así, el texto está mal.

### 1.2 Las cinco capacidades

La tesis completa está en `doc/PLAN-v0.3.md` §0 y replicada en el README. Resumen:

| # | Capacidad | Nativo | nightshift |
|---|---|---|---|
| A | Memoria procedimental: trayectorias causales (hipótesis → tools → señal decisiva → fix) | No. Guarda hechos | Sí. CTE capture |
| B | Alternativas descartadas con precondiciones | No. Auto Dream borra lo contradicho | Sí. Nodo `superseded_by` + `valid_when` |
| C | Cross-repo / cross-harness | No. Sellado por repo | Sí. Abstracción de trayectoria + `deny_paths` |
| D | Consolidación verificable: una trayectoria pasa a procedimiento sólo si reproducirla pasa un gate | No. Juicio del modelo | Sí. Dream gated por verifiers del usuario |
| E | Captura pre-`/compact` del razonamiento intermedio | No | Sí. Hook `PreCompact` |

A, C y D son las capacidades que M4 mide. B y E son habilitadores: sin E no hay
trayectoria completa que consolidar, sin B la consolidación es lossy de la misma
manera que la nativa.

### 1.3 Condiciones de éxito

Cuatro condiciones. Las cuatro son binarias y ninguna es negociable a mitad de camino.

1. **Ganancia medible.** M4 muestra mejora ≥ el umbral pre-registrado en `bench/PREREG.md`
   en al menos dos de las capacidades A / C / D, con cero regresión frente a S0.
   Si no, el proyecto se congela como spec (ver §11, gate de M4).
2. **Fricción de adopción.** *install-to-first-injected-strategy* < 10 min en macOS o
   Linux, cero API keys nuevas. _(sin cambio respecto a v0.2)_
3. **Auditabilidad.** Para cualquier procedimiento inyectado, `/nightshift why <id>`
   reconstruye la trayectoria origen. Un procedimiento cuyo origen no se puede mostrar
   es un bug, no una feature.
4. **Coexistencia.** _(nueva en v0.3)_ nightshift **nunca escribe** en
   `~/.claude/projects/*/memory/` ni en ningún directorio propiedad de Auto Memory.
   Lee `MEMORY.md` **sólo como señal de retrieval** (input al ranking), nunca lo
   modifica, mueve, reordena ni resume. Desinstalar nightshift debe dejar la memoria
   nativa bit-idéntica a como estaría sin nightshift.

La condición 4 se testea, no se promete: el gate de M1 incluye una aserción de que el
dump de la sesión no contiene ninguna escritura bajo el árbol de Auto Memory.

---

## 2. Alcance

### 2.1 Dentro de alcance (v0.3)

- Captura de trayectorias desde Claude Code vía hooks.
- Persistencia local en SQLite.
- Redacción determinista antes de persistir.
- Retrieval estructural e inyección en `SessionStart`.
- Dream en dos fases: `consolidate` y `verify`.
- Scheduler pluggable (`launchd` / `systemd` / `loop`).
- Un benchmark pre-registrado que puede matar el proyecto.

### 2.2 Fuera de alcance (v0.3) — ver `LATER.md`

- Adapter de OpenCode u otro harness. La *abstracción* es cross-harness por diseño
  (§4.4); el *adapter* no se abre hasta M6.
- Publicación en el marketplace de plugins de Claude Code.
- Sincronización remota, multi-máquina o multi-usuario.
- Cualquier dependencia de API remota. Todo el modelo corre local (Qwen).
- Integración con Omarchy / Quattro.

---

## 3. Arquitectura

### 3.1 Componentes

```
┌──────────────────────────────────────────────────────────────┐
│ Claude Code (harness)                                        │
│   hooks ──► ns-hook-* (ejecutables en PATH, sin estado)      │
└─────────────┬──────────────────────────────┬─────────────────┘
              │ stdin JSON                   │ stdout JSON
              ▼                              ▲
      ┌───────────────────────────────────────────────┐
      │ nightshiftd (daemon Python, localhost)        │
      │  ┌─────────┐ ┌──────────┐ ┌────────────────┐  │
      │  │ redact  │ │ capture  │ │ retrieve/rank  │  │
      │  └────┬────┘ └────┬─────┘ └───────┬────────┘  │
      │       └───────────┴───────────────┘           │
      └───────────────────┬───────────────────────────┘
                          ▼
                  ┌───────────────┐      ┌──────────────────┐
                  │ SQLite local  │◄────►│ dream (batch)    │
                  │ trajectories  │      │ consolidate      │
                  │ procedures    │      │ verify (worktree)│
                  └───────────────┘      └────────┬─────────┘
                                                  ▼
                                          ┌──────────────┐
                                          │ Qwen local   │
                                          └──────────────┘
                          ▲
                  ┌───────┴────────┐
                  │ scheduler      │  launchd | systemd | loop
                  └────────────────┘
```

Los hooks son procesos cortos y sin estado: leen JSON de stdin, escriben JSON a stdout.
Si algo falla, el hook sale 0 y no inyecta nada. **nightshift jamás debe bloquear una
sesión.**

**Enmienda 0.3.1 — el daemon está diferido.** En M1+M2 los hooks escriben directo a
SQLite (WAL) en vez de hablar con `nightshiftd`. El daemon existía en v0.2 para amortizar
la carga del modelo local, y capturar no necesita modelo: agregarlo ahora sería un
proceso de fondo más que puede colgarse, en contra de §7.2. Se reabre cuando llegue dream
(M3), que sí carga Qwen. Ver `LATER.md`.

### 3.2 Stack

_(sin cambio respecto a v0.2)_ Daemon en Python, hooks como ejecutables en PATH,
scheduler pluggable, modelo Qwen local. Sin dependencias de API remota (§2.2).

---

## 4. Modelo de datos

La entidad central es `Trajectory`. El esquema normativo y versionado vive en
`schema/trajectory.v1.json`; esta sección explica el porqué de cada campo. Ante
discrepancia, **gana el JSON Schema**.

### 4.1 Ciclo de vida

```
  open ──► closed ──► candidate ──► procedure
                          │              │
                          └──────────────┴──► superseded
                          │
                          └──► discarded
```

- `open` — sesión en curso, se le hace append.
- `closed` — `Stop` la cerró con un `outcome`.
- `candidate` — consolidada por dream fase 1. **Se inyecta con menor peso.**
- `procedure` — verificada por dream fase 2 contra un gate. Peso pleno.
  Una trayectoria **no puede** estar en `procedure` sin un `verified` completo
  (invariante forzado por el schema).
- `superseded` — una trayectoria posterior la contradijo; sobrevive con
  `superseded_by` apuntando a la sucesora.
- `discarded` — abandonada sin señal utilizable.

### 4.2 Campos añadidos en v0.3

| Campo | Tipo | Por qué |
|---|---|---|
| `abstraction` | objeto | Patrón estructural **sin paths, sin nombres de repo, sin identificadores del proyecto**. Es lo único que puede cruzar de repo A a repo B. Capacidad C. |
| `valid_when` | array de precondiciones | Bajo qué condiciones el procedimiento aplica. Sin esto, una alternativa descartada es ruido; con esto, es conocimiento. Capacidad B. |
| `superseded_by` | id o `null` | La trayectoria que la reemplazó. Auto Dream **borra** lo contradicho; nosotros lo conservamos enlazado. Capacidad B. |
| `verified` | `{gate_id, passed_at, run_id}` o `null` | Prueba de reproducción. Los tres campos son obligatorios si el objeto existe: sin `run_id` no hay auditoría. Capacidad D. |

### 4.3 Campos de captura

`steps[]` es la trayectoria causal propiamente dicha. Cada paso lleva `kind`
(`tool_use`, `tool_failure`, `observation`, `hypothesis`, `correction`,
`compact_snapshot`), y dos banderas que hacen el trabajo pesado:

- `decisive` — este paso es donde la señal se volvió concluyente. Es lo que dream
  busca al consolidar; una trayectoria sin ningún paso decisivo rara vez produce
  un procedimiento útil.
- `contradicted` — marcado por `UserPromptSubmit` cuando el usuario corrige
  ("no, eso está mal"). Es la señal negativa más barata y más confiable que tenemos.

### 4.4 Abstracción y cross-harness

`abstraction.pattern` describe la forma del problema y de la solución en términos
que no mencionan el repo. El schema **rechaza** secuencias tipo path en ese campo
(`/algo/`, `~/`, `../`): no como sustituto del redactor, sino como última red.

El mismo campo es lo que hace la trayectoria portable entre harnesses: `steps[].tool`
se normaliza a un vocabulario propio de nightshift (`read_file`, `edit_file`,
`run_shell`, `search`, …) y el nombre nativo del harness queda en
`steps[].tool_native`. Esto habilita el adapter de OpenCode más adelante sin
migración de datos — pero el adapter sigue fuera de alcance (§2.2).

---

## 5. Captura

### 5.1 Hooks

Nombres verificados contra la doc vigente de Claude Code
(`https://code.claude.com/docs/en/hooks`, consultada 2026-08-26).

| Hook | Acción nightshift |
|---|---|
| `SessionStart` | Retrieve por estructura (tipo de tarea + señales del repo). Inyectar ≤ N procedimientos verificados vía `hookSpecificOutput.additionalContext`. Loguear qué se inyectó, con `procedure_id`, para que `/nightshift why` pueda resolverlo. |
| `PostToolUse` | Capturar (`tool_name`, `tool_input` redactado, resumen de `tool_output`, Δ estado) → append a la trayectoria activa. |
| `PostToolUseFailure` | **Añadido en v0.3.** Igual que `PostToolUse` pero con `error_message`. Ver §5.2. |
| `PreCompact` | Snapshot de la trayectoria activa completa antes de que muera el contexto. Ver §5.3. |
| `Stop` | **Sellar el turno**, no cerrar la trayectoria. Ver §5.6. |
| `SessionEnd` | **Añadido en 0.3.1.** Cerrar la trayectoria: `outcome` (`tests_passed` / `user_corrected` / `abandoned`), y el gate asociado si existe. |
| `UserPromptSubmit` | Detectar correcciones ("no, eso está mal") → marcar el paso anterior como `contradicted`; fijar el tipo de tarea; y, **la primera vez que ese tipo deja de ser `general`**, rehacer el retrieval e inyectar (§5.7). No captura el prompt completo. |

### 5.2 Hallazgo: `PostToolUse` no ve los fallos

La doc vigente separa los eventos: `PostToolUse` dispara **cuando la llamada tuvo
éxito**; los fallos van a `PostToolUseFailure`, que recibe `error_message` en lugar
de `tool_output`.

Para nightshift esto no es un detalle: en una trayectoria de debugging **el fallo es
la señal decisiva**. El plan v0.3 §2 lista sólo `PostToolUse`; la spec añade
`PostToolUseFailure` como hook obligatorio de M1. Sin él capturaríamos únicamente el
camino que funcionó, que es exactamente la memoria declarativa que ya tiene el nativo.

### 5.3 Hallazgo: `PreCompact` no trae el transcript

El payload de `PreCompact` es `session_id`, `cwd` y `compaction_reason`
(`manual` | `auto`). No incluye el contexto que está por comprimirse.

Consecuencia de diseño: el "snapshot de la trayectoria activa completa" **se arma
desde el store propio de nightshift**, no desde el payload del hook. `PreCompact`
funciona como *señal de sellado* — "cerrá y marcá lo acumulado hasta acá como
`compact_snapshot`" — no como fuente de datos. Esto refuerza que la captura debe ser
incremental en `PostToolUse` / `PostToolUseFailure`: lo que no se capturó paso a paso
está perdido para cuando llega `PreCompact`.

### 5.4 Formato de salida de hooks

Los campos van anidados bajo `hookSpecificOutput` (con `hookEventName`), no en la
raíz del JSON. `additionalContext` está soportado en `SessionStart`, `UserPromptSubmit`,
`Stop`, `PostToolUse`, `PostToolUseFailure`, `PreCompact` y `PostCompact`.

`additionalContext` y `systemMessage` van a lugares distintos y no son intercambiables:
el primero entra al contexto del modelo, el segundo se muestra en la terminal. nightshift
usa los dos — la memoria inyectada por `additionalContext`, y una línea de estado por
`systemMessage`. Sin la segunda, un plugin que funciona y uno que no hace nada se ven
idénticos desde la terminal.

**Este formato cambia entre versiones de Claude Code.** M1 debe re-verificarlo contra
la doc vigente antes de escribir el primer hook, y dejar el resultado fechado aquí.

### 5.6 Hallazgo: `Stop` dispara por turno, no por sesión

La doc vigente define `Stop` como "cuando Claude termina de responder", y su exit code 2
*impide que Claude termine y continúa la conversación*. Es decir: dispara al final de
**cada turno**, no al final de la sesión. Quien señala el fin de la sesión es `SessionEnd`.

El plan v0.3 §2 le asigna a `Stop` el cierre de la trayectoria. Hacerlo ahí partiría cada
sesión de debugging en tantas trayectorias como turnos tenga, que es exactamente lo
contrario de capturar una cadena causal completa.

Reparto corregido, implementado en M1:

- `Stop` — sella el turno: registra la señal acumulada como un paso `observation`.
- `SessionEnd` — cierra la trayectoria e infiere el `outcome`.

`SessionEnd` pasa a ser hook obligatorio de M1.

### 5.7 Hallazgo: `SessionStart` no puede saber el tipo de tarea

**Añadido en 0.3.2, de correr M2 contra sesiones reales.**

`SessionStart` dispara antes de que el usuario escriba nada. La trayectoria de la sesión
nueva se abre, por lo tanto, con `task_type = general`, que no es un tipo sino "todavía
sin clasificar". El ranking de §5.1 emparejaba entonces `general` con `general`, sumaba
el peso de coincidencia de tarea y reportaba `same_task_type`. Una inyección real dijo
`score 0.90 · same_task_type,same_repo` con las dos trayectorias sin clasificar: el
retrieval decía ser estructural y era por repo y recencia.

Dos correcciones, ambas en M2:

1. `general` **no puntúa** como coincidencia de tipo de tarea. Sigue habiendo retrieval
   en `SessionStart` — por repo, recencia y desenlace — pero el texto inyectado dice qué
   ranking ocurrió en vez de nombrar uno que no ocurrió.
2. El retrieval se **rehace** en el primer `UserPromptSubmit` cuyo prompt clasifica la
   tarea, que es el primer momento de la sesión en que "retrieve por estructura (tipo de
   tarea)" puede cumplirse. Ese hook también admite `additionalContext` (§5.4).

Dos invariantes que la segunda pasada tiene que respetar, y que están testeadas:

- **Nada se inyecta dos veces en la misma sesión.** La tabla `injections` tiene
  `session_id`; lo ya inyectado se filtra del ranking. Repetir una trayectoria no es más
  evidencia, es más contexto gastado.
- **La segunda pasada ocurre una sola vez.** Se dispara en la transición de `general` a
  un tipo, no en cada prompt.

### 5.5 Comandos

Las skills de un plugin llevan el namespace del plugin, así que los nombres reales son
`/nightshift:<skill>` y no `/nightshift <sub>` como suponía el plan:

- `/nightshift:status` — qué hay capturado, qué está `candidate`, qué está `procedure`,
  qué inyectó esta sesión.
- `/nightshift:why <id>` — muestra la trayectoria origen completa. La auditabilidad es
  feature, no debug: es la condición de éxito 3 (§1.3).
- `/nightshift:doctor` — auto-diagnóstico de invariantes y replay end-to-end de los hooks.
- `/nightshift:dev` — estado de desarrollo del propio plugin, para las sesiones que lo
  modifican.
- `/nightshift:dream [--verify]` — **no existe todavía.** Llega con M3 y M5.

Todas son envoltorios finos sobre `nightshift <subcomando>`, que es donde vive la lógica
para poder testearla sin un harness corriendo.

---

## 6. Dream

Dos fases. La fase 2 es nueva en v0.3 y es la que sostiene la capacidad D.

### 6.1 Fase 1 — `consolidate`

_(sin cambio respecto a v0.2)_ Sobre las trayectorias `closed` del período, con el
modelo Qwen local:

1. Agrupar por similitud estructural (tipo de tarea + forma de la trayectoria).
2. Extraer el patrón: hipótesis → señal decisiva → fix.
3. Producir `abstraction` y `valid_when`.
4. Enlazar contradicciones: si una trayectoria nueva contradice una vieja, la vieja
   pasa a `superseded` con `superseded_by` apuntando a la nueva. **No se borra.**
5. Resultado: estado `candidate`.

### 6.2 Fase 2 — `verify` (nueva)

Una trayectoria `candidate` se promueve a `procedure` **sólo si reproducirla pasa el
gate declarado**:

1. Crear un worktree git efímero en el commit registrado en la trayectoria.
2. Re-ejecutar la trayectoria abstraída contra ese worktree.
3. Correr el gate declarado (`gate_id` → un comando del usuario, no un juicio del modelo).
4. Si pasa: `verified = {gate_id, passed_at, run_id}`, estado → `procedure`.
5. Si falla o no es reproducible: queda en `candidate`.
6. Destruir el worktree, pase o falle.

Qué cuenta exactamente como reproducción está en **ADR-002**. Resumen: el gate es un
comando que sale 0 o distinto de 0, provisto por el usuario. nightshift no inventa
gates ni acepta "el modelo dice que funciona" como evidencia.

### 6.3 Peso de inyección

- `procedure` (verificada) — peso pleno.
- `candidate` (no verificada) — **peso menor**, y marcada como no verificada en el
  texto inyectado. El agente debe poder distinguir "esto se probó" de "esto pareció
  funcionar una vez".

Trayectorias no verificables (sin gate declarable, p. ej. una tarea de diseño) no son
un fallo: se quedan en `candidate` de forma permanente y siguen siendo útiles.

---

## 7. Runtime y operación

### 7.1 Scheduler pluggable

Requisito de M3. Tres backends detrás de una interfaz:

| Backend | Plataforma | Notas |
|---|---|---|
| `launchd` | macOS | Target primario. La corrida nocturna asume `caffeinate` y cargador. |
| `systemd` | Linux | Timer de usuario, no unidad de sistema. |
| `loop` | cualquiera | Fallback en foreground. Para desarrollo y para máquinas sin lo anterior. |

El backend se selecciona por config, con autodetección por defecto. El gate de M3 es
operativo, no unitario: **tres noches seguidas sin intervención** en la Air.

### 7.2 Degradación

Si el daemon está caído, el modelo local no está disponible o el store está bloqueado:
los hooks salen 0, no inyectan y no capturan. Una sesión con nightshift roto debe ser
indistinguible de una sesión sin nightshift.

---

## 8. Privacidad y seguridad

Regla de orden: **Histora primero.** El caso de uso más sensible se soporta antes que
el cómodo. Si algo no es seguro para Histora, no se envía a ningún lado.

### 8.1 `deny_paths`

`deny_paths` es **obligatorio y debe existir antes de que se instale el primer hook**.
No es configuración opcional con default vacío: sin `deny_paths` resuelto, el daemon
se niega a capturar.

Todo lo que caiga bajo un `deny_path` no se captura: ni el path, ni el contenido, ni
un hash, ni el hecho de que existe.

### 8.2 Redactor determinista

Toda abstracción cross-repo pasa por un redactor **determinista** — regex más la lista
de identificadores del repo (nombre, remotes, nombres de paquete, dominios internos) —
**antes de persistir**, no antes de exportar. El store nunca contiene el material sin
redactar.

Determinista significa: mismo input, misma salida, sin modelo en el camino. Un LLM no
es un redactor; es una fuente de fugas con buena redacción.

Los tests del redactor corren contra fixtures derivadas de Histora (gate de M1).

### 8.3 Coexistencia con Auto Memory

Repetido acá porque es una regla de seguridad, no sólo de producto: nightshift nunca
escribe en `~/.claude/projects/*/memory/`. Lee `MEMORY.md` como señal de retrieval.
El gate de M1 lo verifica automáticamente sobre el dump.

---

## 9. Interfaz de usuario

Ver §5.5. Principio: todo lo que nightshift inyecta debe ser rastreable hasta su
trayectoria origen con un solo comando.

---

## 10. Benchmark

El diseño completo y los umbrales están en `bench/PREREG.md`, que se congela **antes**
de escribir una línea de código de M1.

### 10.1 Baseline (cambio de v0.3)

`S0` deja de ser "Claude Code sin memoria" y pasa a ser **Claude Code con Auto Memory
y Auto Dream encendidos**. Comparar contra un agente sin memoria era comparar contra
un rival que ya no existe; el resultado hubiera sido bonito y falso.

| Fila | Configuración |
|---|---|
| S0 | Claude Code + Auto Memory + Auto Dream **on** |
| S1 | S0 + nightshift (`candidate` only) |
| S2 | S0 + nightshift (verified) — **sólo tras M5** |

### 10.2 Familias

- **A — Bug recurrente variado.** 10 bugs con causa compartida y síntoma distinto, en
  un repo fixture. Métrica: tasa de resolución y tool calls hasta el fix.
- **C — Transferencia cross-repo.** Mismo patrón estructural (pipeline con
  transformaciones opacas) en dos repos distintos. Métrica: resolución en repo B tras
  aprender en repo A.
- **D — Precisión de consolidación.** Inyectar contradicciones y reversiones; medir
  cuántas memorias inyectadas son falsas o stale al final.

Mismo modelo, mismo seed de tareas, 3 corridas por celda.

### 10.3 Quién decide

Claude Code **no** decide umbrales. Los lee de `bench/PREREG.md`. Un umbral que se
ajusta después de ver el resultado no es un umbral.

---

## 11. Milestones y gates

Un milestone por rama. El gate es un script, no un juicio (excepto M0, cuyo gate
humano es explícito).

| M | Entrega | Gate |
|---|---|---|
| M0 | Docs: spec v0.3, ADR-001, ADR-002, schema versionado, PREREG, README | `make lint-docs` pasa **y** Ismael revisa ADR-001 |
| M1 | Capture: `PostToolUse`, `PostToolUseFailure`, `PreCompact`, `Stop`, `SessionEnd` → SQLite. Redactor con tests | **Código listo.** Gate pendiente: 5 sesiones reales capturadas sin fuga de `deny_paths` (test automatizado sobre el dump) y fixtures de Histora |
| M2 | Retrieve: inyección estructural en `SessionStart`, trayectorias crudas, sin dream | **Código listo.** `/nightshift:why` reconstruye la trayectoria origen de cada inyección |
| M3 | Dream `consolidate` + scheduler pluggable | 3 noches seguidas sin intervención en la Air |
| M4 | **Benchmark — go/no-go** | Mejora ≥ umbral pre-registrado en ≥ 2 de A/C/D, cero regresión en S0 |
| M5 | Dream `verify` (worktree + gate). **Sólo si M4 pasa** | Precisión de `procedure` > `candidate` en re-corrida del benchmark |
| M6+ | OpenCode adapter, marketplace, Omarchy/Quattro | Ver `LATER.md` |

M5 va después de M4 a propósito: `verify` es lo más caro de construir y sólo vale la
pena si la memoria procedimental cruda ya muestra ganancia.

Si M4 falla, el proyecto **se congela como spec**. Eso es un resultado, no un fracaso:
la spec y el benchmark negativo son publicables.

---

## 12. Changelog v0.2 → v0.3

| § | Cambio |
|---|---|
| 1.1 | Positioning reescrito: "procedural memory layer over the agent's native declarative memory". Prohibido el encuadre de reemplazo. |
| 1.3.2 | Sin cambio: install-to-first-injected-strategy < 10 min, cero API keys nuevas. |
| 1.3.4 | **Nueva** condición de coexistencia: nunca escribir en `~/.claude/projects/*/memory/`; `MEMORY.md` sólo como señal de retrieval. |
| 4 | **Nuevos** campos `abstraction`, `valid_when`, `superseded_by`, `verified{gate_id,passed_at,run_id}`. |
| 5.2, 5.3 | **Añadido en spec, no en el plan:** `PostToolUseFailure` como hook obligatorio, y `PreCompact` como señal de sellado en lugar de fuente de datos. Ambos por verificación contra la doc vigente. |
| 6 | Dream pasa a dos fases: `consolidate` (v0.2) + `verify` (nueva). Sólo lo verificado es `procedure`; lo demás queda `candidate` con menor peso. |
| 7.1 | Scheduler pluggable (`launchd`/`systemd`/`loop`) pasa a requisito de M3. |
| 8 | `deny_paths` obligatorio antes del primer hook. Redactor determinista antes de persistir. Histora primero. |
| 10 | Baseline S0: de "sin memoria" a "Auto Memory + Auto Dream on". |
| 11 | Milestones reordenados: benchmark (M4) antes de verify (M5). |

### Enmiendas 0.3.1 (de implementar M1+M2)

| § | Enmienda | Por qué |
|---|---|---|
| 3.1 | El daemon queda diferido; los hooks escriben directo a SQLite | Capturar no necesita modelo local, y un proceso de fondo más es superficie de bloqueo contra §7.2 |
| 5.1, 5.6 | `SessionEnd` pasa a hook obligatorio; `Stop` sella el turno | `Stop` dispara por turno: cerrar ahí partiría cada sesión en N trayectorias |
| 5.5 | Los comandos son `/nightshift:<skill>` | Las skills de plugin llevan namespace; el plan suponía `/nightshift <sub>` |
| 5.1 | `UserPromptSubmit` persiste la **etiqueta** de tipo de tarea, nunca el texto del prompt | El retrieval estructural necesita el tipo; guardar el prompt sería una superficie de privacidad que el plan no pidió |

### Enmiendas 0.3.2 (de correr M2 contra sesiones reales)

| § | Enmienda | Por qué |
|---|---|---|
| 5.1, 5.7 | El retrieval se rehace en el primer `UserPromptSubmit` con tipo de tarea, sin re-inyectar lo ya dicho | `SessionStart` corre antes del primer prompt: ahí el tipo es siempre `general` y el ranking por tipo no puede ocurrir |
| 5.7 | `general` deja de puntuar como coincidencia de tipo de tarea | Emparejaba dos trayectorias sin clasificar y reportaba `same_task_type`: el `why` afirmaba un ranking que no había pasado |
