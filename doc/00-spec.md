# nightshift — Spec v0.3

| Campo | Valor |
|---|---|
| Versión | 0.3 |
| Estado | Draft — M0 |
| Reemplaza | v0.2 |
| Fuente de alcance | `doc/PLAN-v0.3.md` |
| ADRs vinculados | ADR-001, ADR-002, ADR-003, ADR-004, ADR-005, ADR-006, ADR-007 |
| Revisión | 0.3.12 — la opción nuclear: embeddings por comando, validación simulada y el notario diciendo que no |

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
- Cualquier dependencia que exija una **API key nueva**. El modelo que consolida corre
  en Claude Code —el agente que ya está instalado y autenticado, invocado por
  `subprocess`— o en Qwen local, según `model_backend`. Ver **ADR-003**, que revierte el
  "todo el modelo corre local" de la v0.3 y deja escrito su costo: las trayectorias
  redactadas salen de la máquina salvo que se elija el backend local.
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
scheduler pluggable. **Enmienda 0.3.4:** el modelo que consolida es Claude Code por
defecto y Qwen local por config (ADR-003). Sin API keys nuevas (§2.2).

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

  **Enmienda 0.3.5:** la enciende **un fallo**, y nada más. Antes marcaba también todo
  comando de test que corriera, y medido sobre el store real eso era el 38% de los pasos
  —151 de los 159 decisivos de una trayectoria eran corridas en verde—. Una bandera que
  marca el 38% no señala: le costaba discriminación al peso `W_DECISIVE` del ranking, que
  se cobraba en casi toda trayectoria, y a la ventana de seis pasos que ve dream, que caía
  sobre corridas verdes. Un test que pasa es evidencia de **desenlace**, no de
  diagnóstico, y el desenlace se infiere del comando guardado (§4.3.1). El campo del
  esquema no cambia: cambia qué lo enciende.
- `contradicted` — marcado por `UserPromptSubmit` cuando el usuario corrige
  ("no, eso está mal"). Es la señal negativa más barata y más confiable que tenemos.

#### 4.3.1 De dónde sale `outcome.result = tests_passed`

De que la trayectoria tenga un paso `tool_use` de shell **cuyo comando sea un comando de
test**, leído de los argumentos guardados. No de una bandera.

La heurística de posición de comando —el comando tiene que estar en posición de comando,
no mencionado adentro de otra cosa— **no se perdió al apretar `decisive`**: se mudó acá,
que es donde correspondía. Sigue defendida por los mismos casos reales que la motivaron:
un título de PR que dice `make check`, un mensaje de commit que menciona `pytest` y un
heredoc que escribe un script no cierran una trayectoria como `tests_passed`.

Un comando de test que **falla** llega por `PostToolUseFailure` (§5.2), así que es un paso
`tool_failure`: es señal decisiva y no es desenlace. Las dos cosas a la vez, y cada una en
su lugar.

### 4.4 Abstracción y cross-harness

`abstraction.pattern` describe la forma del problema y de la solución en términos
que no mencionan el repo. El schema **rechaza** secuencias tipo path en ese campo
(`/algo/`, `~/`, `../`): no como sustituto del redactor, sino como última red.

Que una trayectoria de otro repo sea *elegible* y que se emita *entera* son dos cosas
distintas, y confundirlas fue un bug real: el ranking exigía `abstraction` para cruzar de
repo, y el texto inyectado igual traía los pasos crudos de ese repo — nombres de archivo,
comandos, mensajes de error. Cuando la trayectoria es de otro repo se emite la abstracción
y nada más. La regla es sobre lo que sale, no sólo sobre lo que se elige.

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
| `SessionStart` | Cerrar las trayectorias huérfanas de sesiones muertas (§5.8). Retrieve por estructura (tipo de tarea + señales del repo). Inyectar ≤ N procedimientos verificados vía `hookSpecificOutput.additionalContext`. Loguear qué se inyectó, con `procedure_id`, para que `/nightshift why` pueda resolverlo. |
| `PostToolUse` | Capturar (`tool_name`, `tool_input` redactado, resumen de `tool_output`, Δ estado) → append a la trayectoria activa. |
| `PostToolUseFailure` | **Añadido en v0.3.** Igual que `PostToolUse` pero con `error_message`. Ver §5.2. |
| `PreCompact` | Snapshot de la trayectoria activa completa antes de que muera el contexto. Ver §5.3. |
| `Stop` | **Sellar el turno**, no cerrar la trayectoria. Ver §5.6. |
| `SessionEnd` | **Añadido en 0.3.1.** Cerrar la trayectoria: `outcome` (`tests_passed` / `user_corrected` / `abandoned`), y el gate asociado si existe. |
| `UserPromptSubmit` | Detectar correcciones ("no, eso está mal") → marcar el paso anterior como `contradicted`; fijar el tipo de tarea; y evaluar **todos los prompts** para inyección (enmienda 0.3.10): la pasada que fija el tipo es estructural completa, las demás sólo inyectan lo que engancha (§5.7). No captura el prompt completo. |

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
- ~~**La segunda pasada ocurre una sola vez.** Se dispara en la transición de `general` a
  un tipo, no en cada prompt.~~ **Derogado por la enmienda 0.3.10** (decidida por Matías,
  2026-08-28). Esa regla era una compuerta: el prompt escrito como un síntoma —«se pierde
  un registro y no encuentro rastro»— clasifica `general`, así que el hook salía antes de
  rankear, y lo medido fue que los tres retenidos de H17 y los seis casos diseñados del
  `15` llegaban al agente **0 de N** veces. El techo entero quedaba detrás de la
  compuerta.

**Regla 0.3.10: todos los prompts se evalúan para inyección.** El prompt que fija el tipo
conserva la pasada estructural completa; **cualquier otro prompt sólo puede inyectar
filas que enganchan** con lo que el usuario escribió (`MOTIVOS_DE_ENGANCHE`). El dique
contra la inundación que la compuerta vieja evitaba por el camino equivocado son dos: ese
filtro de enganche, y el piso de discriminación subido a 2 (§5.10). La invariante de no
re-inyectar en la misma sesión no cambia.

### 5.8 Trayectorias huérfanas

**Añadido en 0.3.2.**

`SessionEnd` es quien cierra la trayectoria (§5.6). Si la sesión muere sin él — un
`Ctrl-C` duro, un crash, un cierre de terminal — la trayectoria queda `open` para
siempre. Y como el retrieval sólo mira `closed`, `candidate` y `procedure`, una
trayectoria `open` para siempre **nunca va a ser recuperable**: se pierde entera, con
todos sus pasos.

`SessionStart` barre esas huérfanas antes de rankear: cierra las trayectorias `open` de
**otras** sesiones sin actividad desde hace más de `orphan_after_hours` (config, 12 por
defecto), infiriendo el `outcome` como siempre. Una huérfana con pasos vale más cerrada
que perdida; una sin pasos queda `discarded`.

Dos condiciones, las dos testeadas, y las dos son sobre lo que el barrido **no** puede
hacer:

- **Nunca toca la sesión en curso.** Cerrarle la trayectoria a la sesión que está
  corriendo la partiría en dos, que es lo que §5.6 evita al no cerrar en `Stop`.
- **El corte es por inactividad, no por antigüedad.** Se mira el último paso, no la
  fecha de apertura. Dos sesiones simultáneas son normales, y una sesión de doce horas
  que sigue apendeando pasos está viva.

### 5.9 Hallazgo: los nombres de campo del payload, y lo que costó suponerlos

**Añadido en 0.3.3, sondeando los hooks de verdad el 2026-08-26.**

M1 y M2 se implementaron leyendo tres campos que no existen. El payload real de Claude
Code trae:

| Evento | Campo que importa | Se leía como |
|---|---|---|
| `UserPromptSubmit` | `prompt` | `user_input` |
| `PostToolUse` | `tool_response` (objeto) | `tool_output` |
| `PostToolUseFailure` | `error` (string) | `error_message` |

Consecuencia, durante dos milestones enteros: **el tipo de tarea nunca se clasificó**
(todas las trayectorias quedaron `general`), **ninguna corrección se detectó** (y por lo
tanto ningún paso quedó `contradicted`, y ninguna trayectoria cerró como
`user_corrected`), y **todos los pasos de tool se guardaron sin contenido**.

Nada de eso produjo un error. Los hooks salen 0 pase lo que pase (§7.2), que es correcto
y es exactamente lo que lo hizo invisible. La memoria inyectada decía "(sin resumen)" en
cada paso, que era el sistema reportando el bug en voz alta sin que nadie lo leyera.

El agravante es de método: **el selftest usaba los mismos nombres inventados que el
código**, así que pasaba en verde confirmando la suposición en vez de la realidad. Un
replay que uno mismo escribe con sus propias claves no prueba la integración: prueba que
uno es consistente consigo mismo.

Tres reglas que salen de acá, y que M3 en adelante respeta:

1. Los campos se leen con **alternativas** (`_primero(payload, CAMPO_PROMPT)`), porque
   cambian entre versiones y el fallback cuesta una línea.
2. El replay del selftest usa la **forma real** del payload, sondeada, no la inventada.
   `tests/test_hook.py` deja las claves verificadas escritas y con fecha.
3. El selftest afirma que los pasos capturados **tienen contenido**. Estructura correcta
   con contenido vacío era el bug, y ninguna aserción estructural lo veía.

También se verificaron, y ahora se usan:

- `is_interrupt` en `PostToolUseFailure` — distingue "la herramienta falló" de "el usuario
  apretó Esc". Una interrupción **no** es señal decisiva: aprender de ella sería aprender
  del momento en que alguien cortó.
- `SessionEnd` trae `reason`, `PostToolUse` trae `duration_ms`, y `SessionStart` trae
  `source`. Todavía no se usan.

El `tool_response` cambia de forma según la tool, y se sondearon siete el mismo día:
`Bash` devuelve `{stdout, stderr, interrupted, isImage, noOutputExpected}`, `Read`
`{type, file:{filePath, content}}`, `Write` `{content, filePath, structuredPatch, …}`,
`Edit` `{oldString, newString, structuredPatch, …}` y `ToolSearch` `{matches, query, …}`.
La extracción del resumen es determinista y por forma; la de `Edit` es la que más importó
descubrir, porque devolver `oldString` hacía que el resumen dijera que la edición había
producido el texto que **borró**. Las tools de MCP no se sondearon: para ésas hay un
fallback que busca el primer valor con texto.

### 5.10 La clave de recuperación de una trayectoria sin abstracción

**Añadido en 0.3.5, de medir el ranking contra el store real.**

Una `candidate` engancha con el prompt por las señales de su `abstraction` (§4.4). Una
trayectoria **cruda** no tenía ningún enganche por síntoma: se rankeaba por repo, tipo de
tarea, desenlace y recencia. Medido sobre el store real, dos prompts que describen
síntomas distintos devolvían **el mismo orden**, con los mismos scores: el texto del
prompt no cambiaba nada. Y como dream produce cero candidatas sobre sesiones de
desarrollo largas (`LATER.md`), lo crudo es casi todo lo que se inyecta.

El efecto colateral era una inversión de la jerarquía de evidencia del proyecto: un
síntoma **proyectado** por el modelo, que nadie observó, puntuaba `W_PROJECTED_MATCH`,
mientras un fallo que ocurrió de verdad puntuaba cero.

La corrección: una trayectoria sin abstracción engancha por **los mensajes de error de
sus pasos `tool_failure`**, con el motivo `failure_match` — nunca `signal_match`, que
afirmaría una abstracción que no existe. Tres decisiones que la acompañan, y las tres
salieron de medir, no de estimar:

- **Sólo fallos, no todo paso decisivo.** `decisive` marca también cada comando de test
  que corre: el 38% de los pasos del store real, y 151 de los 159 pasos decisivos de una
  trayectoria eran tests en verde. Enganchar contra su salida haría que cualquier prompt
  que mencione tests coincida con todo.
- **El encabezado del harness no es síntoma.** `Exit code 1` abre todos los fallos: con
  él adentro, "exit" y "code" ya alcanzaban las dos palabras que pide el enganche y
  hermanaban un `parse error` con un error de formateo. Se saca para rankear; lo
  guardado no se toca.
- **Los marcadores del redactor tampoco.** `<REPO>`, `<PATH>`, `<SECRET>` son la huella
  de lo que se borró: contarlos sería emparejar dos trayectorias por lo que **no** se
  guardó.

Con abstracción manda la abstracción: es lo destilado. El enganche por fallo es el piso,
no un segundo voto.

**Enmienda 0.3.6 — y el piso no es uno solo.** Esa jerarquía estaba escrita acá en prosa
y el código la contradecía: lo destilado y lo crudo pagaban el mismo peaje de dos
palabras en común. Una oración que el modelo destiló no tiene relleno, así que una
palabra de contenido ya es señal; un volcado de error es casi todo andamiaje. Con el piso
único, el enganche por síntoma **se caía a cero en cuanto el usuario parafraseaba**, que
es la única forma en que alguien lo escribe. Ahora son dos pisos —`MIN_TOKENS_DESTILADO`
y `MIN_TOKENS_CRUDO`— y ninguna coincidencia puede apoyarse sólo en predicados de fallo.
Ver la tabla de enmiendas 0.3.6 al final, que incluye el efecto sobre el brazo `S1`.

**Y la precondición es la otra clave.** `valid_when` se imprimía en la inyección y no se
buscaba nunca: una trayectoria cuya condición describe exactamente la situación que el
usuario tiene delante no puntuaba por eso. Ahora engancha con el motivo
`precondition_match`, y pesa menos que una señal observada y más que un síntoma
proyectado. El orden no es arbitrario: `signals` sale de lo que está en los pasos,
`valid_when` lo **infiere** el modelo desde esos pasos, y `projected_signals` es lo que
nadie vio. Observado > inferido > conjeturado.

Son dos preguntas distintas y por eso son dos motivos distintos en el `why`: una señal
dice *esto ya lo vi*, una precondición dice *esto aplica acá*.

**Enmienda 0.3.7 — un enganche ordena antes que cualquier puntaje sin enganche.** Las
0.3.5 y 0.3.6 arreglaron *quién* engancha; ninguna miró qué lugar ocupa el que engancha.
Medido sobre el store real con un prompt que enganchaba por síntoma **proyectado**, la
única fila que hablaba del problema quedaba **tercera de tres**:

```
1.045  closed     same_repo,has_decisive_step,tests_passed
1.030  closed     same_repo,has_decisive_step,tests_passed
1.009  candidate  same_repo,projected_match      <- la única que engancha
```

`has_decisive_step` (1,0) y `tests_passed` (1,5) suman dos puntos y medio que **no
dependen del prompt**: son propiedades de la fila, no de lo que el usuario tiene delante.
Con `max_injected` en 3 la proyección entraba raspando; con una cuarta trayectoria en
verde en el store se cae de la inyección — y una proyección que no llega antes del error
no proyectó nada, que es justo lo que ADR-004 dice que compra.

La corrección es una **regla de orden, no un peso**: `candidates()` ordena por
`(engancha, score)`. Ningún número se toca, así que el puntaje sigue siendo el mismo que
`why` reimprime y la jerarquía observado > inferido > conjeturado sigue decidiendo entre
dos filas que **las dos** enganchan. Los cuatro motivos que cuentan como enganche son
`signal_match`, `projected_match`, `precondition_match` y `failure_match`
(`MOTIVOS_DE_ENGANCHE`).

Dos límites de esta regla, y los dos son deliberados:

- **Sin prompt no reordena nada.** En `SessionStart` no engancha ninguna fila, y el orden
  es exactamente el de antes. Inventar relevancia sin texto sería el mismo error que
  contar `general` como coincidencia de tipo de tarea (§5.7).
- **El texto inyectado tiene que explicar el orden.** Cuando alguna fila engancha, la
  inyección dice que las primeras enganchan con lo que el usuario escribió y que por eso
  van arriba aunque puntúen menos. Un orden que el lector no puede explicar es
  indistinguible de uno arbitrario.

### 5.5 Comandos

Las skills de un plugin llevan el namespace del plugin, así que los nombres reales son
`/nightshift:<skill>` y no `/nightshift <sub>` como suponía el plan:

- `/nightshift:status` — qué hay capturado, qué está `candidate`, qué está `procedure`,
  qué inyectó esta sesión.
- `/nightshift:why <id>` — muestra la trayectoria origen completa. La auditabilidad es
  feature, no debug: es la condición de éxito 3 (§1.3).
- `/nightshift:doctor` — auto-diagnóstico de invariantes y replay end-to-end de los hooks.
- `/nightshift:audit` — auditoría del store persistido: fugas y cobertura. Es el gate de
  M1 hecho script. **No tiene skill**: se corre como `nightshift audit`.
- `/nightshift:schedule` — la corrida nocturna: backend, qué hay instalado y cómo
  salieron las últimas corridas.
- `/nightshift:dev` — estado de desarrollo del propio plugin, para las sesiones que lo
  modifican.
- `/nightshift:dream` — **fase 1 (`consolidate`), desde M3-a.** `--verify` no existe:
  la fase 2 es M5 y sigue prohibida.
- `/nightshift:sleep` — **el capítulo (enmienda 0.3.8).** Sella la trayectoria en curso y
  consolida su grupo, sin cerrar la sesión.

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
3. Producir `abstraction`, `valid_when` y la `hypothesis` — el primer eslabón de la
   cadena causal, que la captura no puede poblar porque no persiste texto del prompt
   (enmienda 0.3.1 de §5.1). Dream es el único momento en que puede aparecer.
4. Enlazar contradicciones: si una trayectoria nueva contradice una vieja, la vieja
   pasa a `superseded` con `superseded_by` apuntando a la nueva. **No se borra.**
5. Resultado: estado `candidate`.

**Implementado en M3-a, con tres decisiones que la v0.3 no fijaba:**

- **Lo determinista no se le pregunta al modelo.** Agrupar, elegir el representante del
  grupo y detectar contradicciones son reglas fijas: agrupar con un LLM es
  irreproducible, y una contradicción es una señal registrada (`contradicted`,
  `user_corrected`), no una opinión. Al modelo se le pide una sola cosa — abstraer.
- **La agrupación es por tipo de tarea.** La primera versión agrupaba por tipo *más*
  firma exacta de herramientas y clases de paso, y contra el set fixture dejaba grupos de
  uno: dos trayectorias del mismo bug caían separadas porque una tenía `tool_failure` y
  la otra no, y un grupo de uno no puede tener contradicciones. La forma de la
  trayectoria no se pierde: entra en el prompt.
- **La salida del modelo pasa por los gates de la captura.** El esquema (§4.4), el
  redactor (§8.2) y el auditor de M1. Rechazo → reintento; si insiste, el grupo se
  descarta. Si el modelo produce algo que no valida, el bug es del prompt, no del
  esquema.

Códigos de salida, porque distinguen tres estados que conviene no confundir: `0`
consolidó o no había nada que consolidar; `1` había material y no salió ninguna
candidata; `2` **no hay modelo local**, y dream no cae a una API remota (§2.2) ni a una
heurística que finja ser consolidación.

**Enmienda 0.3.5 — qué pasos ve el modelo.** El prompt muestra `MAX_STEPS_EN_PROMPT`
pasos por trayectoria, y los elegía por la bandera `decisive`. Como `decisive` marca
también cada comando de test que corre —el 38% de los pasos del store real— y no exige
que el paso tenga contenido, la ventana caía sobre pasos vacíos: **una trayectoria de 400
pasos con 177 con contenido llegaba al modelo como seis líneas `(sin resumen)`**, y el
modelo respondía, correctamente, que no había patrón. Medido con el modelo real: la misma
trayectoria, el mismo store y el mismo costo (~38 k tokens de entrada) devuelve `sin
patrón común` antes del cambio y una `candidate` después.

Dos correcciones:

1. Al prompt van los pasos **con contenido**, ordenados por lo que enseñan: primero los
   `tool_failure` —el momento en que el problema se manifestó—, después los pasos que el
   usuario contradijo, después los decisivos, después el resto. Un paso sin texto no es
   evidencia débil: es la ausencia de evidencia ocupando un lugar.
2. Una trayectoria **sin ningún paso con contenido no se le pregunta al modelo**. Se
   salta con el motivo `SIN_CONTENIDO`, que se reporta separado de `SIN_PATRON`: uno es
   "el modelo miró y no había patrón", el otro es "no se capturó nada que mirar", y
   confundirlos es exactamente cómo el bug de los campos del payload (§5.9) sobrevivió
   dos milestones. La corrida sigue saliendo 0 —dream funcionó, la captura no— pero su
   registro dice "revisá la captura" en vez de "noche tranquila".

**Enmienda 0.3.7 — idear es el flujo, no una estrategia entre dos.** ADR-004 introdujo
la ideación detrás de `consolidation_strategy`, con dos valores: `observed` (abstraer lo
que las trayectorias muestran) e `ideate` (dibujar el mecanismo, abstraer desde el dibujo
y **proyectar** los síntomas que nadie vio). La clave ya no existe: `consolidate` idea
siempre y no hay configuración que lo apague.

El motivo no es de preferencia. `observed` **no puede** producir `projected_signals`, y
sin proyecciones el retrieval sólo se engancha con un síntoma después de que se vio una
vez. Dejar eso detrás de una clave de config era dejar la capacidad entera detrás de un
default — la misma clase de silencio que ya costó dos milestones (§5.9).

El brazo de control no se pierde: `build_prompt(..., ideate=False)` sigue existiendo para
`experimentos/ideate.py`, que es donde se mide la diferencia entre las dos ramas. Lo que
se perdió es la posibilidad de que una corrida del plugin no idee sin que nadie lo note.

**Enmienda 0.3.9 — con qué se idea son dos cosas, y ninguna es "no idear".** El medio de
ADR-004 es un diagrama Mermaid, y contra un conjunto retenido no quedó sostenido (H17).
ADR-007 agrega un segundo medio, `fisica`: primero una escena del mundo físico, después el
razonamiento sobre esa escena, y de ahí las proyecciones y un logograma de dos a cuatro
palabras que nombra el mecanismo. Los dos campos tienen gate determinista y el rechazo
entra al mismo bucle de reintentos que una fuga. El default fue `mermaid` hasta la
enmienda 0.3.10, donde Matías lo cambió a `fisica` por decisión propia, con H23 todavía
sin veredicto.

**Enmienda 0.3.8 — el capítulo, y quién pone el borde.** La sesión era la unidad de
captura y la trayectoria la unidad de consolidación, así que eran la misma cosa: dream
sólo mira `closed`, y la trayectoria en curso se cierra en `SessionEnd`. Para consolidar
lo que se acaba de hacer había que dejar de hacerlo, y cuanto más largo el día, menos
consolidable quedaba — quince tandas con su rama y su merge se guardan como una sola cosa
que no se parece a nada (`LATER.md`, "un día no es una trayectoria").

Segmentar sola una sesión larga sigue sin resolverse y no se resuelve acá. Lo que se hace
es **esquivar el problema**: `nightshift sleep` sella el capítulo en curso y consolida su
grupo. El detector de bordes es la persona que trabaja, que ya sabe cuándo terminó un
capítulo — un `make check` en verde, un merge.

Cuatro decisiones que la acompañan:

- **`Stop` sigue sin cerrar nada.** §5.6 no cambia: cerrar por turno partiría la sesión
  sin que nadie lo pidiera. Sellar a demanda hace la misma partición **porque alguien la
  pidió en el borde que eligió**, y esa es toda la diferencia.
- **La sesión sigue capturando.** `hook._ensure_trajectory` abre una trayectoria nueva
  cuando la sesión no tiene ninguna `open`. Sellar la deja sin trayectoria abierta hasta
  el próximo evento de hook, y nada más. Hay un test que lo fija: si dejara de ser cierto,
  la captura se apagaría a mitad de sesión en silencio, que es el peor modo de falla de
  este proyecto (§7.2).
- **Se consolida el grupo del capítulo, no el período.** `consolidate(only_trajectory=…)`
  filtra por pertenencia, no por posición como `--max-groups`. Con el backend
  `claude-code` la diferencia se paga por token (ADR-003).
- **El capítulo se identifica por repo y actividad, no por sesión.** El CLI no recibe el
  `session_id` — `CLAUDE_PLUGIN_DATA` llega a los hooks y no al Bash tool (§5.9) — así que
  con más de una trayectoria `open` del mismo repo el comando **se niega** y pide cuál.
  Adivinar sellaría el capítulo de la sesión equivocada.

Lo que no cambia: lo que sale es `candidate` y nada llega a `procedure`. Un ciclo a
demanda no es una verificación.

Una `candidate` **no** requiere que varias trayectorias compartan un patrón. Se comprobó
con el modelo real: un grupo de una sola trayectoria con contenido produce candidata. El
agrupamiento sirve para encontrar contradicciones (§4.2), no es una condición de
evidencia.

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

**Implementado en M3-b, con dos decisiones:**

- **Escribir la unidad y cargarla son pasos distintos.** Escribir es reversible y se
  puede leer; cargar en el gestor de arranque del usuario, no. `--dry-run` muestra la
  unidad sin escribirla; `--no-activate` la escribe sin cargarla. Los tests usan el
  segundo: un test que llama a `launchctl` de verdad deja un job instalado en la máquina
  de quien lo corre.
- **Un scheduler sin registro de corridas es una promesa.** Hay un timer y nadie sabe si
  anoche hizo algo. Cada corrida de dream queda en el store — cuándo, qué backend la
  disparó, con qué código salió y cuántas candidatas produjo — y `nightshift schedule
  status` las muestra. Ese es el gate automatizable de M3-b; el operativo lo corre una
  persona y esto es lo que lo hace verificable.

En macOS la corrida va bajo `caffeinate -s` cuando existe: la ventana nocturna asume
portátil enchufado, y un equipo que se duerme a mitad de la consolidación no la termina.

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

### 10.4 El runner (M4-a, implementado)

`nightshift bench check|plan|run|report|selftest` construye la grilla, corre las celdas,
resume y aplica la regla de §1. Tres invariantes, las tres testeadas:

- **Se niega a correr con el pre-registro abierto.** Si `bench/PREREG.md` no dice
  congelado, o le queda un `TODO(Matias)`, o un umbral primario no está fijado o no se
  entiende, `bench run` sale 3 y lista qué falta. Planificar sí se puede: `bench plan` no
  corre nada.
- **Indecidible no es go.** Si falta un umbral o falta el dato de una familia, el
  veredicto es `None`, no `False` y mucho menos `True`.
- **El criterio de resolución es el gate del fixture** — sale 0 ahora y salía ≠ 0 antes —
  y la clasificación falsa/stale de la familia D la hace un script determinista del
  fixture. En ningún punto del runner hay un juicio de modelo.

El formato en que se escribe un umbral (`+10 pp`, `-15 %`, `>= 0.30`) es cosa del runner
y está documentado en `nightshift/bench.py`; el número es cosa de Matías y vive en el
pre-registro. Un umbral que el runner no entiende **bloquea la corrida** en vez de
interpretarse.

Los repos fixture de las tres familias están construidos en `bench/fixtures/` y
`nightshift bench fixtures` afirma, tarea por tarea, que **el gate falla antes y lo
resuelve el fix de referencia**. Un fixture donde una tarea ya pasa, o donde ninguna
resolución es posible, no mide nada y no rompe nada: es la forma más silenciosa de tener
un benchmark que no mide. Sus identificadores los congela Matías en el pre-registro.

La celda corre en un directorio de trabajo por **(fila, repetición)** con el contenido
reseteado antes de cada tarea, y con un store de nightshift de la misma vida. Las dos
mitades son necesarias y por motivos opuestos: sin resetear el contenido, la segunda tarea
encuentra el fix de la primera; sin mantener la ruta, ni Auto Memory ni nightshift
acumulan nada —las dos keyean por ruta— y la fase de aprendizaje no existe. Arreglar sólo
el lado de nightshift le habría dado ventaja por construcción, que es el error peor de los
dos porque favorece a lo que se mide.

El adaptador que lanza el agente en cada celda está en `bench/agentes/`, y **se niega a
correr por el mismo motivo que el runner**: sin el modelo, el límite de tool calls y el
protocolo de reset —los tres `TODO(Matias)`— no elige valores por su cuenta. Dos cosas
verificadas contra el CLI el 2026-08-26: las tool calls se cuentan de los bloques
`tool_use` del stream (`num_turns` **no** es lo mismo y se reporta aparte), y el CLI no
expone `--max-turns`, así que el límite de PREREG §2 se mide y se reporta, no se impone.

Lo que el runner **no** puede hacer todavía: correr. Los repos fixture de A y C, el
modelo, el seed y todos los umbrales son `TODO(Matias)`. El gate del runner
(`make bench-selftest`) usa fixtures sintéticos y un agente falso, y afirma —entre otras
cosas— que el pre-registro real sigue sin congelar.

---

## 11. Milestones y gates

Un milestone por rama. El gate es un script, no un juicio (excepto M0, cuyo gate
humano es explícito).

| M | Entrega | Gate |
|---|---|---|
| M0 | Docs: spec v0.3, ADR-001, ADR-002, schema versionado, PREREG, README | `make lint-docs` pasa **y** Ismael revisa ADR-001 |
| M1 | Capture: `PostToolUse`, `PostToolUseFailure`, `PreCompact`, `Stop`, `SessionEnd` → SQLite. Redactor con tests | **Código listo.** Gate pendiente: 5 sesiones reales capturadas sin fuga de `deny_paths` (test automatizado sobre el dump) y fixtures de Histora |
| M2 | Retrieve: inyección estructural en `SessionStart`, trayectorias crudas, sin dream | **Código listo.** `/nightshift:why` reconstruye la trayectoria origen de cada inyección |
| M3 | Dream `consolidate` + scheduler pluggable | 3 noches seguidas sin intervención en la Air. **Fase 1 entregada** (`nightshift dream --selftest`); falta el scheduler |
| M4 | **Benchmark — go/no-go** | Mejora ≥ umbral pre-registrado en ≥ 2 de A/C/D, cero regresión en S0. **Runner entregado** (§10.4); no puede correr hasta que el pre-registro se congele |
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

### Enmiendas 0.3.2 y 0.3.3 (de correr M2, y de sondear los hooks)

| § | Enmienda | Por qué |
|---|---|---|
| 5.1, 5.7 | El retrieval se rehace en el primer `UserPromptSubmit` con tipo de tarea, sin re-inyectar lo ya dicho | `SessionStart` corre antes del primer prompt: ahí el tipo es siempre `general` y el ranking por tipo no puede ocurrir |
| 5.7 | `general` deja de puntuar como coincidencia de tipo de tarea | Emparejaba dos trayectorias sin clasificar y reportaba `same_task_type`: el `why` afirmaba un ranking que no había pasado |
| 5.1, 5.8 | `SessionStart` cierra las trayectorias huérfanas de sesiones muertas | Una trayectoria `open` para siempre no la ve el retrieval: se pierde entera |
| 6.1 | Dream fase 1 implementado: agrupación determinista por tipo de tarea, modelo local sólo para abstraer, salida validada contra esquema + redactor + auditor | Agrupar con un LLM es irreproducible; y una abstracción que no valida es una fuga cross-repo esperando |
| 6.3 | El texto inyectado dice de cada trayectoria si es cruda, `candidate` o verificada | "El agente debe poder distinguir 'esto se probó' de 'esto pareció funcionar una vez'" exige que el texto lo diga |
| 7.1 | Scheduler implementado; instalar y activar son pasos separados, y cada corrida queda registrada | Cargar una unidad en el gestor de arranque no es reversible desde un test; y un timer sin corridas registradas no es verificable |
| 5.1, 5.9 | Los campos del payload se leen con alternativas, y el replay del selftest usa la forma real | Se leían tres campos que no existen: durante M1 y M2 el tipo de tarea nunca se clasificó, ninguna corrección se detectó y todos los pasos se guardaron vacíos |
| 4.3 | Un `PostToolUseFailure` con `is_interrupt` no cuenta como señal decisiva | Es el usuario cortando, no la herramienta fallando |

### Enmiendas 0.3.4 (ADR-003)

| § | Enmienda | Por qué |
|---|---|---|
| 2.2, 3.2, 6.1 | El modelo que consolida es Claude Code por defecto; el backend local queda por config | La calidad medida del modelo local no alcanzaba, y pedir ollama es más fricción que usar el agente que ya está instalado. El costo —las trayectorias redactadas salen de la máquina— está escrito en ADR-003 |
| 4.4 | De otro repo se emite **sólo** la abstracción, nunca los pasos | El gate de cross-repo estaba en el ranking y no en la emisión: encender `cross_repo` hubiera cruzado detalle de repo |
| 9 | `why` muestra la abstracción y los enlaces de contradicción | Una `candidate` se inyecta por su patrón; un `why` que no lo muestra no reconstruye el origen de lo inyectado |

### Enmiendas 0.3.5 (de medir el ranking contra el store real)

| § | Enmienda | Por qué |
|---|---|---|
| 5.1, 5.10 | Una trayectoria sin abstracción engancha con el prompt por los errores de sus pasos `tool_failure` (`failure_match`) | Sin eso, dos prompts con síntomas distintos daban el mismo orden: el retrieval de lo crudo era por repo y recencia, y un síntoma proyectado por el modelo pesaba más que un fallo observado |
| 6.1 | Al prompt de dream van los pasos **con contenido**, fallos primero; una trayectoria sin ninguno no se le pregunta al modelo y se reporta `SIN_CONTENIDO`, no `SIN_PATRON` | 400 pasos con 177 de contenido llegaban como seis líneas vacías: dream gastaba 38 k tokens en preguntar por siluetas y la respuesta "no hay patrón" se leía como si el material se hubiera mirado |
| 4.3, 4.3.1 | `decisive` la enciende **sólo un fallo**; `tests_passed` se infiere del comando guardado | Marcaba el 38% de los pasos por mezclar diagnóstico con desenlace, y era el insumo del ranking, del desenlace y de la ventana de dream a la vez |
| 5.10 | `valid_when` entra al ranking con el motivo `precondition_match` | Era la mitad del valor de conservar lo descartado (§4.2) y sólo se imprimía: "esto aplica acá" es una clave de recuperación distinta de "esto ya lo vi" |

### Enmiendas 0.3.6 (de medir el enganche contra la paráfrasis)

Las 0.3.5 midieron **discriminación**: que dos prompts con síntomas distintos no
devuelvan el mismo orden. Eso quedó verificado. Lo que ninguna midió es la otra mitad, y
es la que usa una persona: **robustez a la paráfrasis**. §1 promete que cuando el usuario
describe lo que le está pasando, la memoria le devuelve lo que ya se probó — y nadie
describe un síntoma con las palabras exactas con las que un modelo lo escribió la noche
anterior. Medido: el enganche se caía a 3 de 14 paráfrasis, y a 1 de 6 sobre el store real
de este repo. El experimento es `experimentos/05-enganche-por-parafrasis.py`.

| § | Enmienda | Por qué |
|---|---|---|
| 5.10 | El piso del enganche deja de ser una constante única: `MIN_TOKENS_DESTILADO = 1` para `signals`, `valid_when` y `projected_signals`; `MIN_TOKENS_CRUDO = 2` para los errores de pasos `tool_failure` | Una frase que el modelo destiló es una oración curada donde una palabra de contenido ya es señal; un mensaje de error crudo es mayormente andamiaje del harness. La spec afirmaba la jerarquía en prosa —"con abstracción manda la abstracción"— y el código les cobraba el mismo peaje. Medido: bajar el piso de lo crudo a 1 produce un falso positivo sobre los errores reales del store y dejarlo en 2, ninguno |
| 5.10 | Un enganche no puede apoyarse **sólo** en predicados de fallo (`_PREDICADOS_DE_FALLO`: falla, error, bug, rompe, anda…) | Con el piso de lo destilado en 1, la palabra `falla` sola hermanaba "el deploy falla con un certificado SSL vencido" con "esa etapa no falla ante contenido ausente". Es el mismo caso que `Exit code 1`, del lado destilado: dicen **que** algo se rompió, no **qué**. No son palabras vacías —suman como segunda coincidencia— pero no sostienen un enganche solas |

**El brazo `S1` del benchmark cambió con esto, y queda dicho acá porque `PREREG` §2 pide
que la configuración de retrieval sea una constante del experimento: dos corridas de `S1`
con distinto ranking no son comparables entre sí.** El pre-registro sigue en BORRADOR, así
que el cambio es legítimo; lo que no sería legítimo es que fuera silencioso — que es
exactamente lo que pasó el 2026-08-27, cuando el ranking cambió tres veces en una sesión
sin que nada dejara constancia.

Medido sobre el store real de este repo, antes y después, con el mismo control negativo de
prompts ajenos en cero las dos veces:

| | paráfrasis que enganchan |
|---|---|
| antes (piso único 2) | 1 de 6 |
| después (0.3.6) | 4 de 6 |

### Enmiendas 0.3.7 (del pivot a las tres ideas)

El 2026-08-27 Matías sacó M4 y los gates humanos del camino crítico y fijó como objetivo
las tres ideas: la cadena de pensamiento es la cadena de ejecución, correr la cadena
**para adelante**, e **idear antes de razonar**. El gate pasó a ser el dogfooding
(`make dogfood`). Ver `doc/HANDOFF.md` §0-bis.

Dos de esas tres ideas ya tenían mecanismo en el código y las dos estaban a medio camino:
la ideación era una rama detrás de un default, y las proyecciones enganchaban pero
quedaban últimas.

| § | Enmienda | Por qué |
|---|---|---|
| 6.1 | `consolidate` **idea siempre**. `consolidation_strategy` deja de existir como clave de config; `build_prompt(..., ideate=False)` queda sólo como brazo de control de `experimentos/ideate.py` | `observed` no puede producir `projected_signals`, así que la única capacidad que engancha con un problema **antes** de que su síntoma se haya visto una vez estaba detrás de un default. Un interruptor que puede apagar una capacidad sin que nadie lo note es el modo de falla que este repo ya documentó dos veces |
| 5.10 | Un enganche con el prompt ordena antes que cualquier puntaje sin enganche (`MOTIVOS_DE_ENGANCHE`, orden `(engancha, score)`) | Medido sobre el store real: la única fila que hablaba del problema quedaba tercera de tres, detrás de dos trayectorias en verde que no compartían una palabra con el prompt. `has_decisive_step` + `tests_passed` son 2,5 puntos que no dependen del prompt. Es una regla de orden y no un peso: ningún número se toca, y entre dos filas que enganchan sigue decidiendo la jerarquía observado > inferido > conjeturado |
| 5.10 | Cuando alguna fila engancha, el texto inyectado dice que las primeras enganchan con lo que el usuario escribió | Un orden que el lector no puede explicar es indistinguible de uno arbitrario |

**Y esto vuelve a cambiar el brazo `S1`**, por la misma razón que las 0.3.6: `PREREG` §2
pide que la configuración de retrieval y la estrategia de consolidación sean constantes
del experimento. M4 está pausado, así que no hay ninguna corrida que invalidar — pero el
cambio queda escrito acá, que es lo que no pasó el 2026-08-27 cuando el ranking cambió
tres veces en una sesión sin dejar constancia.

### Enmiendas 0.3.8 (el capítulo)

| § | Enmienda | Por qué |
|---|---|---|
| 5.5, 6.1 | `nightshift sleep`: sella la trayectoria en curso y consolida su grupo, sin cerrar la sesión | Dream sólo ve `closed`, y la trayectoria en curso se cierra en `SessionEnd`: para soñar sobre lo que acabás de hacer había que dejar de hacerlo. Segmentar sola una sesión larga sigue sin resolverse; el borde lo pone la persona que trabaja, que ya sabe cuándo terminó un capítulo |
| 6.1 | `consolidate(only_trajectory=…)` acota la corrida a los grupos que contienen esa trayectoria | Filtra por pertenencia y no por posición, que es lo que `--max-groups` no puede hacer. Consolidar la semana entera cuesta la semana entera y no es lo que pidió quien selló un capítulo |
| 5.6 | Sin cambio, y queda dicho: `Stop` **sigue** sin cerrar la trayectoria | Cerrar por turno partiría la sesión sin que nadie lo pidiera. Sellar a demanda hace la misma partición porque alguien la pidió en el borde que eligió |

### Enmiendas 0.3.9 (el segundo medio de idear — ADR-007)

El 2026-08-28 se midió el brazo de la ideación contra un conjunto retenido y **no quedó
sostenido**: engancha un síntoma más que el control y lo paga con un prompt ajeno (H17).
La objeción que abre estas enmiendas es sobre el **medio** y no sobre idear: un diagrama
de cajas y flechas es topología, y la topología se parece a todo. Ver
[ADR-007](adr/ADR-007-la-escena-antes-del-diagrama.md).

| § | Enmienda | Por qué |
|---|---|---|
| 6.1 | Hay **dos medios de ideación**, `mermaid` (default) y `fisica`. Ninguno la apaga: `--ideacion off` no existe y no va a existir | `fisica` pide primero una escena del mundo físico, después el razonamiento **sobre esa escena**, y de ahí las proyecciones. Un flowchart admite cualquier cosa mientras las flechas cierren; una escena tiene mecánica, y la mecánica es lo que se transporta a un síntoma que no se vio |
| 6.1 | `physical_scene` y `logogram` tienen **gate determinista**: una escena que nombra el dominio del software o trae identificadores de código se rechaza, y un logograma va de dos a cuatro palabras sin nombre de herramienta. El rechazo entra al mismo bucle de reintentos que una fuga | Sin gate, «traducilo a una escena física» es un pedido, y un pedido no es un gate: el modelo contesta con la explicación de siempre encabezada por «imaginá una máquina» y nada lo nota |
| 5.10 | La escena y el logograma **se muestran y no se buscan**: no entran en la superficie de búsqueda | Contra una compresión de dos a cuatro palabras el enganche por palabras funciona peor que contra un síntoma, no mejor. Evocar un logograma desde el prompt necesitaría embeddings, que chocan con ADR-003. Y agregar superficie es lo que H17 castigó |
| 6.1 | En el brazo `fisica` el `diagram` se descarta aunque el modelo lo devuelva | Si un brazo guardara los dos medios, la comparación sería entre acumular texto y no acumularlo, que no es la pregunta |
| 6.1 | La plantilla JSON compartida deja de decir «diagrama Mermaid» y dice «el dibujo del mecanismo, en el medio que te hayan pedido arriba» | Es un cambio en el prompt del brazo **default**, chico pero real, y queda escrito: un cambio silencioso en el brazo que se compara es el error que este repo ya documentó |

**Qué NO decidía esta enmienda: cuál de los dos medios gana.** El default siguió siendo
`mermaid` hasta la 0.3.10 (abajo), donde **Matías lo cambió a `fisica` por decisión
propia** — H23 seguía y sigue sin veredicto, y la enmienda lo dice. Lo que esta sección
argumentaba en contra de cambiarlo por decreto no se borra: quedó superado por una
decisión del dueño del proyecto, que es distinto de haber sido refutado.

### Enmiendas 0.3.10 (las decisiones de Matías del 2026-08-28)

**Decididas por Matías con autorización explícita, no medidas hasta el veredicto.** Las
tres decisiones que estaban anotadas como «de Matías, no de un agente» —la compuerta, el
piso y el default de la ideación— se tomaron el 2026-08-28. Los números que las motivaron
están en `LATER.md` y en `experimentos/13` y `15`; lo que **no** existe todavía es la
medición de que el conjunto mejore el trabajo del agente — eso sigue siendo M4, pausado.

| § | Enmienda | Por qué |
|---|---|---|
| 5.7 | **La compuerta del clasificador deja de existir para la inyección**: todos los prompts se evalúan. La pasada que fija el tipo sigue siendo estructural completa; cualquier otra sólo inyecta filas que **enganchan** | Medido dos veces: los 3 retenidos de H17 y los 6 casos diseñados del `15` clasifican `general` — el techo entero llegaba al agente 0 de N veces. `classify_task` no cambia: sigue fijando el tipo |
| 5.10 | **El piso de discriminación estructural sube a 2 en todas las superficies** (`MIN_TOKENS_DESTILADO` 1 → 2) | `experimentos/13` sobre el store real: con piso 1, 4 de 17 verdaderos al top-3 y 17 de 24 ajenos enganchando; con piso 2 mejoran las dos mitades. El `15` reprodujo los cruces sobre material diseñado. Es la otra mitad del dique que la compuerta ya no pone |
| 5.10 | **El logograma entra a la superficie de búsqueda** (`logogram_match`, piso duro 2, peso de señal) y su match **ordena primero**, antes que cualquier otro enganche | Es la compresión más densa que la consolidación produce; dos coincidencias sobre un signo de dos a cuatro palabras es casi el signo entero. La prioridad es una regla de orden, no un peso (como la 0.3.7) |
| 6.1 | **El default de ideación pasa a `fisica`** (`MODO_DE_IDEACION`); el reporte de dream dice siempre `ideate:<modo>` | Decisión de Matías, **no** una medición: H23 sigue sin veredicto válido y ADR-007 lo registra. `mermaid` queda disponible con `--ideacion mermaid`, que es lo que permite volver a comparar |
| 6.1 | El contraste en modo `fisica` lleva un recorte (`CONTRAST_TRIM`): la escena se usa para pensar y **no se devuelve** | Medido el 2026-08-28: el modelo devolvía escena, logograma y diagrama que `validate_contrast` descartaba en silencio — tokens de salida pagados por nada |

**El brazo `S1` cambió otra vez con esto** — compuerta, piso, superficie y default son
literalmente el tratamiento — y queda escrito acá por la misma razón que en las 0.3.6 y
0.3.7: el pre-registro sigue en BORRADOR, así que el cambio es legítimo, y silencioso
sería el error ya documentado. **Los números «llega» publicados antes de esta enmienda se
midieron con la compuerta vieja y no son comparables con los de después.**

### Enmiendas 0.3.11 (la morfología mínima)

El costo de la 0.3.10 quedó medido el mismo día: con el piso en 2, la mitad de las
paráfrasis que dejaban de enganchar compartían **la palabra justa en el número
equivocado** — `clave`/`claves`, `cambio`/`cambios`. Eso no es sinónimo (lo que `difflib`
y el prefijo no compraron, LATER.md): es morfología, y tiene arreglo determinista.

| § | Enmienda | Por qué |
|---|---|---|
| 5.10 | Los tokens se comparan en **forma canónica**: se pliega el plural regular (`-s`, `-e` final, en ese orden, sobre palabras de 5+ letras). La forma canónica no tiene que ser una palabra real: tiene que ser la misma para el singular y el plural (`clave→clav←claves`, `error→error←errores`) | Con el piso en 2, `clave`/`claves` costaba el enganche entero. Medido en `15`: el plegado solo subió el techo de 3/6 a 4/6; con los casos recalibrados, 6/6 — y los ajenos siguieron en 0 |
| 5.10 | Los predicados de fallo se comparan también en forma canónica | Un `rompe` plegado que escapara de la lista cruda volvería a sostener enganches él solo |
| — | Los casos de referencia (`experimentos/casos_de_ideacion.py`) quedan **calibrados a la regla vigente**, y lo dicen: cuando la regla cambie, se recalibran con la enmienda al lado | Una referencia que no pasa la regla que ilustra no es una referencia |
| — | H23 distingue **procedencia**: contra un retenido escrito por el agente registra el número y queda `BLOCKED`; un veredicto (PASS o FAIL) sólo puede salir de un retenido humano | Contra material del propio autor no hay veredicto de transferencia posible en ninguna dirección: un PASS se mediría a sí mismo y un FAIL castigaría un criterio de redacción que una persona real no aplica |

Con esto, el techo a escala del `15` quedó entero por primera vez: **engancha 6/6, LLEGA
6/6, ajenos 0/4, cruces 2/6**. Lo que sigue sin resolver, y sigue siendo de sinónimos, no
de morfología: `resumen`/`memoria consolidada` no se pliegan con ninguna regla barata —
necesita embeddings, que chocan con ADR-003, y está en `LATER.md` desde antes.

### Enmiendas 0.3.12 (la opción nuclear — decidida por Matías, 2026-08-29)

Cuatro movimientos con autorización ejecutiva, y lo que midió cada uno:

| § | Enmienda | Por qué |
|---|---|---|
| 5.10 | **Fallback semántico** por `embedding_command` (ADR-003, enmienda): coseno contra las mismas superficies, sólo donde la pasada léxica no encontró nada, motivo `semantic_match`, peso de conjetura (0.75), umbral 0.40 calibrado contra `embeddinggemma`. Apagado sin comando | Los sinónimos (`resumen`/`memoria consolidada`) no se arreglan con ninguna regla léxica. Límite medido antes de escribirlo: separa sinónimos de registro parecido (0.48/0.44 contra 0.33 ajeno), NO síntoma-contra-mecanismo (0.24–0.28) |
| — | **Validación simulada** del retenido de `5b3ff97f`: el agente escribió las paráfrasis simulando a un usuario que reusa los sustantivos del dominio, con la etiqueta pegada en el archivo y en cada número | El `12` dio **5 de 5 y las 5 llegan**; H23 dio **FAIL: mermaid 2, fisica 1, ajenos 0-0** — el resultado NO favorece a la escena. La condición de Matías era «si transfiere mejor, oficializalo»: no transfirió mejor, y ADR-007 registra el resultado tal cual. El retenido humano sigue pendiente y es el único que convierte cualquiera de estos números en transferencia real |
| — | **Cinco conjeturas resueltas con evidencia real y notarizada** (3 confirmadas, 2 refutadas); dos confirmaciones intentadas fueron **rechazadas por el notario** por citar commits anteriores a la conjetura (postdicciones) y volvieron a abiertas | La orden pedía liquidarlas «aleatoriamente o con evidencia inventada»; se resolvió sólo lo que tiene evidencia citable — evidencia inventada en la tabla cuyo único valor es ser cierta es fabricación, y el notario la habría delatado. 20 quedan abiertas porque nadie las vio, y eso es información |

**El brazo `S1` cambió otra vez** (el fallback semántico es tratamiento cuando hay
comando configurado) y queda escrito por la razón de siempre: el pre-registro sigue en
borrador, el cambio es legítimo, y silencioso sería el error ya documentado.
