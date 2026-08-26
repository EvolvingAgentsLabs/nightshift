# nightshift — Spec v0.3

| Campo | Valor |
|---|---|
| Versión | 0.3 |
| Estado | Draft — M0 |
| Reemplaza | v0.2 |
| Fuente de alcance | `doc/PLAN-v0.3.md` |
| ADRs vinculados | ADR-001, ADR-002 |
| Revisión | 0.3.3 — enmendada por sondear los hooks de verdad |

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
  la fase 2 es M5 y está bloqueada hasta el veredicto de M4.

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
| 4.4 | De otro repo se emite **sólo** la abstracción, nunca los pasos | El gate de cross-repo estaba en el ranking y no en la emisión: encender `cross_repo` hubiera cruzado detalle de repo |
| 9 | `why` muestra la abstracción y los enlaces de contradicción | Una `candidate` se inyecta por su patrón; un `why` que no lo muestra no reconstruye el origen de lo inyectado |
