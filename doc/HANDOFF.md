# HANDOFF — control del desarrollo

Documento para la sesión de Claude Code que continúa el desarrollo de nightshift.
Se lee entero antes de tocar nada.

---

## 0. Qué sos en esta sesión

Estás corriendo **dentro del plugin que vas a modificar**. Si la sesión se abrió con
`claude --plugin-dir .`, los hooks que están capturando esta conversación son el código
de este working tree. Editar `nightshift/hook.py` cambia cómo se captura tu próxima
tool call.

Eso tiene dos consecuencias prácticas:

- Podés probar tus cambios contra vos mismo. `nightshift status` a mitad de sesión te
  muestra la trayectoria que estás generando ahora.
- Un bug que rompa la captura no te va a dar un error: los hooks salen 0 siempre
  (spec §7.2). El silencio no es evidencia de que funciona. Por eso existe
  `nightshift selftest`, y por eso hay que correrlo.

Arrancá con `nightshift dev`.

---

## 1. Estado real

### Construido y en `main`

| Pieza | Dónde |
|---|---|
| Captura por 7 hooks | `nightshift/hook.py`, `hooks/hooks.json` |
| Redactor determinista | `nightshift/redact.py` |
| Store SQLite + export `trajectory.v1` | `nightshift/store.py` |
| Retrieval estructural e inyección | `nightshift/retrieve.py` |
| CLI y skills | `nightshift/cli.py`, `skills/` |
| Gate | `make check` — lint-docs, lint-code, schema, 42 tests, selftest |

### No construido

Dream (`consolidate` y `verify`), el scheduler, el benchmark. **Hoy nada llega a
`candidate` ni a `procedure`**, así que ninguna memoria inyectada está verificada.
No lo describas como si lo estuviera, ni en el README, ni en un commit, ni en una demo.

### Bloqueado por una persona, no por vos

- **M4 (benchmark go/no-go)** — lee umbrales de `bench/PREREG.md`, donde hay 19
  `TODO(Matias)`. **Completar uno es una violación, no una ayuda.** Podés construir el
  runner del benchmark; no podés inventar los números que decide.
- **M5 (verify)** — prohibido empezarlo antes del veredicto de M4. No es una
  preferencia de estilo: verify es lo más caro de construir y sólo vale la pena si la
  memoria procedimental cruda ya mostró ganancia (plan §3).
- **Gate humano de M0** — la revisión de ADR-001 por Ismael sigue pendiente, y M1/M2 ya
  se construyeron sobre las cinco capacidades que ese ADR decide. Si la revisión tumba
  una fila, hay código que sobra. No lo des por cerrado.

---

## 2. Reglas que no se negocian

Están en `CLAUDE.md` y las repito porque son las que se rompen sin querer:

1. **Un milestone por rama.** PR sólo si el gate pasa, y el gate es un script.
2. **Cada sesión termina en commit medible.** Si no hay commit, el motivo va a
   `LATER.md`. No hay tercera opción.
3. **Sólo librería estándar.** Ningún import de tercero, en `nightshift/` ni en
   `tests/`. `make lint-code` lo verifica.
4. **Sin red.** Ningún `socket`, `urllib`, `http`, `requests` en `nightshift/`.
   El modelo local se invoca por `subprocess`, no por HTTP.
5. **Nunca escribir bajo `~/.claude/projects/*/memory/`.** Sólo `config.py`,
   `context.py` y `cli.py` pueden siquiera nombrar esa ruta.
6. **Los hooks nunca bloquean ni ensucian stdout.** Salida: JSON válido o nada.
7. **No agregues features que no estén en el plan.** Si parece buena idea, va a
   `LATER.md`.

---

## 3. Hechos ya verificados — no los re-derives

Verificados contra `https://code.claude.com/docs/en/hooks` el 2026-08-26, y algunos
descubiertos corriendo el plugin. Están en la spec; acá van resumidos para que no
pierdas tiempo redescubriéndolos:

- `PostToolUse` **no dispara en fallos**. Los fallos van a `PostToolUseFailure`.
- `PreCompact` **no trae el transcript**: sólo `session_id`, `cwd`, `compaction_reason`.
  Es señal de sellado, no fuente de datos.
- `Stop` dispara al final de **cada turno**, no de la sesión. Cierra `SessionEnd`.
- `additionalContext` va al contexto del modelo; `systemMessage` a la pantalla del
  usuario. No son intercambiables.
- Las skills de plugin llevan namespace: `/nightshift:status`, no `/nightshift status`.
- Los cambios en `nightshift/*.py` **no** necesitan `/reload-plugins` — cada hook
  arranca un proceso nuevo. El reload es para `hooks/hooks.json`, skills y manifiesto.
- `CLAUDE_PLUGIN_DATA` llega a los hooks pero **no** al Bash tool. Por eso el store se
  fija en `~/.nightshift` y esa variable se ignora a propósito.

Si alguno deja de ser cierto porque cambió el harness, actualizá `doc/00-spec.md` §5 en
el mismo commit y dejá la fecha.

---

## 4. Cola de trabajo

En orden. Cada tarea es una rama, y cada una trae su gate — un comando que sale 0 o no.
No pases a la siguiente sin que la anterior esté en `main`.

### T1 — `nightshift audit` · desbloquea el gate de M1

**Por qué primero.** El gate de M1 es "5 sesiones reales capturadas sin fuga de
`deny_paths`, test automatizado sobre el dump". Ese comando **no existe**, así que hoy
M1 no se puede cerrar aunque el plugin se use cien veces. Es la pieza que falta entre
"código listo" y "M1 pasado".

**Qué construir.** `nightshift audit [--min-sessions N] [--json]` que abre el store
real y afirma, sobre todo lo persistido:

- ninguna cadena matchea un patrón de `deny_paths`;
- ningún patrón de `redact.SECRET_RULES` matchea nada (si el redactor dejó pasar un
  secreto, acá se ve);
- no hay rutas absolutas del home del usuario;
- `abstraction.pattern` no contiene secuencias tipo path;
- reporta cuántas sesiones distintas, trayectorias y pasos hay.

Sale 1 si encuentra algo, o si hay menos de `--min-sessions` sesiones.

**Cuidado:** el reporte no puede imprimir el material que encontró en claro. Decí
*dónde* (trayectoria, paso, campo) y *qué regla* saltó, nunca el valor.

**Gate:** `nightshift audit --min-sessions 5` sale 0 sobre el store real de Matías, más
un test que siembra una fuga a mano en un store desechable y verifica que `audit` la
encuentra. Un auditor que nunca falla no es un auditor.

---

### T2 — retrieval por tipo de tarea · el bug real de M2

**El problema.** `SessionStart` corre **antes** de que el usuario escriba nada, así que
el `task_type` de la trayectoria nueva todavía es `general`. El ranking termina
emparejando `general` con `general`: parece que matchea por tipo de tarea, y no lo hace.
La frase de la spec "retrieve por estructura (tipo de tarea)" hoy no se cumple.

Se ve en la práctica: una inyección real reportó
`score 0.90 · same_task_type,same_repo` cuando ambas trayectorias eran `general`.

**Qué construir.** Re-hacer el retrieval en el **primer `UserPromptSubmit`** de la
sesión, cuando ya hay prompt y por lo tanto `task_type`. Ese hook también admite
`additionalContext`.

Dos cosas que hay que resolver bien:

- **No duplicar.** Si algo ya se inyectó en `SessionStart`, no se re-inyecta. La tabla
  `injections` tiene `session_id`; usala.
- **No inyectar en cada prompt.** Sólo la primera vez que el `task_type` deja de ser
  `general`.

**Gate:** un test que siembra una trayectoria `debug_test_failure`, dispara
`SessionStart` (que no matchea por tipo), después `UserPromptSubmit` con un prompt de
debugging, y afirma que la segunda inyección trae `same_task_type` y que ninguna
trayectoria se inyectó dos veces en la misma sesión.

---

### T3 — trayectorias huérfanas

**El problema.** Si la sesión muere sin `SessionEnd` (un `Ctrl-C` duro, un crash), la
trayectoria queda `open` para siempre. Nunca se cierra sola, y como el retrieval sólo
mira `closed`/`candidate`/`procedure`, **nunca va a ser recuperable**. Se pierde entera.

**Qué construir.** Al arrancar `SessionStart`, cerrar las trayectorias `open` de otras
sesiones con más de N horas (config, default razonable) infiriendo el outcome como
siempre. Una huérfana con pasos vale más cerrada que perdida.

**Gate:** test que crea una trayectoria `open` vieja, dispara `SessionStart` de otra
sesión, y verifica que quedó cerrada y que la de la sesión en curso **no** se tocó.

---

### T4 — M3-a: dream `consolidate`

Recién acá empieza M3. Rama nueva.

**Qué construir.** Lo que dice spec §6.1, sobre las trayectorias `closed` del período:
agrupar por similitud estructural, extraer el patrón (hipótesis → señal decisiva → fix),
producir `abstraction` y `valid_when`, enlazar contradicciones poniendo la vieja en
`superseded` con `superseded_by` apuntando a la nueva — **sin borrarla** — y dejar el
resultado en `candidate`.

**El modelo corre local.** Qwen por `subprocess`. Si no hay modelo local disponible,
`dream` **falla y lo dice**; no cae a una API remota, ni a una heurística que finja ser
consolidación. Un `consolidate` que no consolidó tiene que salir distinto de 0.

**El gate más lindo que tenemos.** Toda trayectoria consolidada tiene que seguir
validando contra `schema/trajectory.v1.json`, y el esquema **rechaza paths en
`abstraction.pattern`**. O sea: el esquema que congeló M0 es la red que atrapa al modelo
si filtra rutas del repo al abstraer. No la desactives ni la relajes — si el modelo
produce algo que no valida, el bug es del prompt, no del esquema.

**Gate:** `nightshift dream` sobre un set fixture de trayectorias produce ≥1
`candidate`, todas validan contra el esquema, y ninguna `abstraction.pattern` contiene
el nombre del repo fixture ni una ruta. Más un test de que una contradicción produce
`superseded_by` y **no** un borrado.

---

### T5 — M3-b: scheduler pluggable

**Qué construir.** `launchd` (macOS, target primario), `systemd` (timer de usuario, no
unidad de sistema), `loop` (foreground, para desarrollo). Backend por config con
autodetección. Algo tipo
`nightshift schedule install|status|uninstall [--backend auto|launchd|systemd|loop]`.

**Gate del script:** `nightshift schedule status` reporta las últimas corridas y sus
resultados. **Gate real de M3, que no es tuyo:** tres noches seguidas sin intervención
en la Air. Eso lo corre Matías; vos dejás el comando que lo hace verificable.

---

### Bloqueado — no empieces

- **M4.** Podés construir el runner del benchmark (las tres familias, las filas S0/S1,
  el reporte). **No** podés fijar umbrales ni decidir criterios de éxito: eso es
  `bench/PREREG.md` y es de Matías. Y el pre-registro se congela **antes** de correr
  nada.
- **M5.** Prohibido hasta que M4 dé veredicto.
- **Adapter de OpenCode.** Prohibido. La abstracción ya es cross-harness por diseño
  (spec §4.4) justamente para que el adapter no requiera migrar datos, pero el adapter
  no se toca.

---

## 5. Cómo se entrega cada tarea

```sh
git checkout -b <rama>
# ... trabajás ...
make check          # lint-docs + lint-code + schema + tests + selftest
nightshift selftest # otra vez, desde la sesión, contra el código nuevo
git commit
git push -u origin <rama>
```

PR sólo con el gate en verde. En el cuerpo del PR: qué cambió, **qué gate lo prueba**, y
qué quedó afuera.

**Antes de cada commit, dos preguntas honestas:**

1. ¿Agregué un test que falla si mi cambio se revierte? Si no, no agregué un test.
2. ¿Estoy describiendo lo que construí, o lo que quería construir? El README y los
   commits de este repo dicen explícitamente qué no funciona. Mantené eso.

Si el gate no pasa y no sabés por qué, **no lo relajes**. Los checks de `lint-code` no
son estilo: cada uno defiende una prohibición del proyecto. Un check que molesta es
casi siempre un check que está haciendo su trabajo.

---

## 6. Prompt de arranque

Para pegar en la sesión que toma el control:

```
Leé doc/HANDOFF.md entero, después CLAUDE.md y doc/00-spec.md.

Tu tarea es T1 de la cola: implementar `nightshift audit`, que es lo que
desbloquea el gate de M1. Rama propia, gate en verde, PR.

No toques T2 en adelante hasta que T1 esté en main. No completes ningún
TODO(Matias). No empieces M5. Terminá con un resumen de qué quedó en LATER.md.
```
