# nightshift

**Una capa de memoria procedimental sobre la memoria declarativa nativa del agente.**

*[Read this in English](README.md)*

> **Estado: M1 + M2 — capture y retrieve, corriendo como plugin de Claude Code.**
> Captura trayectorias de sesiones reales, las redacta de forma determinista e
> inyecta las previas al arrancar. **Dream todavía no existe**, así que nada está
> verificado y todo lo inyectado es evidencia débil — etiquetada como tal a propósito.
> El benchmark go/no-go (M4) no se corrió. Ver [Milestones](#milestones).

Claude Code ya trae **Auto Memory** (notas declarativas por repositorio) y **Auto
Dream** (consolidación en background). nightshift **no los reemplaza** y no compite en
"notas + sueño". Corre encima.

> Auto Memory recuerda *qué es verdad en este repo*. nightshift recuerda *cómo se
> averiguó*, y sólo lo asciende a procedimiento cuando reproducirlo pasa un gate.

## Por qué molestarse — las cinco capacidades

nightshift sólo invierte donde lo nativo no puede llegar **por diseño**, no por
inmadurez. Lo que el harness pueda sacar el trimestre que viene no es un foso, así que
no entra al roadmap.

| # | Capacidad | Nativo | nightshift |
|---|---|---|---|
| A | Memoria procedimental: trayectorias causales (hipótesis → tools → señal decisiva → fix) | No. Guarda hechos | Sí. CTE capture |
| B | Alternativas descartadas con precondiciones | No. Auto Dream borra lo contradicho | Sí. Nodo `superseded_by` + `valid_when` |
| C | Cross-repo / cross-harness | No. Sellado por repo | Sí. Abstracción de trayectoria + `deny_paths` |
| D | Consolidación verificable: una trayectoria pasa a procedimiento sólo si reproducirla pasa un gate | No. Juicio del modelo | Sí. Dream gated por verifiers del usuario |
| E | Captura pre-`/compact` del razonamiento intermedio | No | Sí. Hook `PreCompact` |

El razonamiento detrás de cada fila — en concreto *por qué lo nativo no puede hacerlo
por diseño* — está en [ADR-001](doc/adr/ADR-001-no-competir-con-auto-dream.md).

## El proyecto se puede matar solo

M4 es un benchmark go/no-go pre-registrado cuyo baseline (`S0`) es **Claude Code con
Auto Memory y Auto Dream encendidos**, no un agente sin memoria. Si nightshift no le
gana por los umbrales escritos en [`bench/PREREG.md`](bench/PREREG.md) **antes de que
exista el código**, el proyecto se congela como spec.

Eso es un resultado, no un fracaso: la spec más un benchmark negativo son publicables.

## Qué no es

- No es un reemplazo, fork ni parche de Auto Memory. Nunca escribe bajo
  `~/.claude/projects/*/memory/`; lee `MEMORY.md` sólo como señal de retrieval.
  Desinstalar nightshift debe dejar la memoria nativa bit-idéntica.
- No es un servicio en la nube. Sin dependencias de API remota, sin API keys nuevas.
  El modelo corre local.
- No sirve para tareas de una sola pasada. El valor aparece donde importa el *proceso*
  — debugging recurrente, transferencia entre repos — y no debe fingir lo contrario.

## Instalarlo y correrlo

nightshift es un plugin de Claude Code. **Sin dependencias**: sólo librería estándar de
Python 3.9+, nada que instalar, ninguna API key.

```sh
git clone https://github.com/EvolvingAgentsLabs/nightshift
cd nightshift
./bin/nightshift init        # escribe la config; sin deny_paths no se captura
claude --plugin-dir .        # cargarlo por una sesión
```

`init` no es ceremonia opcional: sin `deny_paths` resuelto la captura queda apagada y
`SessionStart` lo dice en vez de capturar (spec §8.1).

Al arrancar, nightshift imprime una línea de estado (`nightshift: capturando · …`). La
memoria inyectada **no** se imprime: va al contexto de Claude por `additionalContext`,
que la terminal nunca muestra. `/nightshift:status` lista lo que se inyectó de verdad.

Para iterar sobre el plugin: los cambios en `nightshift/*.py` aplican en el próximo
evento de hook, porque cada hook corre un proceso nuevo. `/reload-plugins` hace falta
cuando cambiás `hooks/hooks.json`, una skill o el manifiesto.

### Skills

| Skill | Qué hace |
|---|---|
| `/nightshift:status` | Qué hay capturado y qué se inyectó en esta sesión |
| `/nightshift:why <id>` | Reconstruye la trayectoria origen de una inyección — el gate de M2 |
| `/nightshift:doctor` | Chequeo de invariantes en runtime más un replay end-to-end de los siete hooks |
| `/nightshift:dev` | Estado de desarrollo del plugin, para las sesiones que lo modifican |
| `/nightshift:dream` | Fase 1 (`consolidate`) sobre las trayectorias cerradas, con el modelo local |
| `/nightshift:schedule` | La corrida nocturna: qué backend, qué hay instalado y cómo salieron las últimas |

`/nightshift:dream --verify` no existe: la fase 2 es M5 y está bloqueada hasta el
veredicto de M4. **Nada llega a `procedure`, así que nada de lo inyectado está
verificado.**

### Hooks que registra

`SessionStart` · `UserPromptSubmit` · `PostToolUse` · `PostToolUseFailure` ·
`PreCompact` · `Stop` · `SessionEnd`

Tres de ésos son correcciones al plan original, salidas de leer la doc vigente y después
de correr la cosa:

- `PostToolUse` no dispara en fallos: van a `PostToolUseFailure`. En una trayectoria de
  debugging el fallo *es* la señal decisiva.
- `PreCompact` no trae el transcript, así que el snapshot se arma desde el store propio.
  Es señal de sellado, no fuente de datos.
- `Stop` dispara al final de **cada turno**, no de la sesión. Sella el turno;
  `SessionEnd` cierra la trayectoria.
- Una sesión que muere sin `SessionEnd` deja su trayectoria `open` para siempre, y el
  retrieval nunca la ve. `SessionStart` cierra esas huérfanas — sólo de otras sesiones, y
  sólo si no hubo actividad en `orphan_after_hours` (spec §5.8).
- `SessionStart` corre **antes** de que escribas, así que ahí el tipo de tarea todavía es
  `general`. El retrieval por estructura se rehace en el primer prompt que clasifica la
  tarea, sin repetir nada de lo ya inyectado (spec §5.7).

### Qué guarda, y dónde

`~/.nightshift/trajectories.sqlite3` — una sola ubicación, la ejecute quien la ejecute.
Se mueve con `NIGHTSHIFT_HOME` si hace falta. Nunca dentro de tu repo,
y nunca bajo `~/.claude/projects/*/memory/` — un guard en `config.py` levanta si alguna
ruta de código lo intenta, y un test afirma que una sesión completa deja la memoria
nativa intacta.

Todo se redacta **antes** de persistir, con un redactor determinista: regex más los
identificadores del propio repo, sin modelo en el camino. Lo que cae bajo `deny_paths`
no se captura en absoluto — ni el path, ni el contenido, ni el hecho de que ocurrió.

## Estructura del repositorio

```
.claude-plugin/plugin.json     Manifiesto del plugin
hooks/hooks.json               Los siete hooks que registra
bin/                           ns-hook (entrypoint de hooks) y nightshift (CLI), van al PATH
skills/                        /nightshift:status | why | doctor | dev | dream | schedule
nightshift/                    La implementación. Sólo librería estándar
  config.py                      Rutas, deny_paths, el guard de escritura de Auto Memory
  redact.py                      Redactor determinista — corre antes de persistir
  store.py                       SQLite; export_trajectory() emite trajectory.v1
  context.py                     Fingerprint del repo, clasificación de tarea, normalización
  hook.py                        Despacho de hooks. Nunca levanta, siempre sale 0
  retrieve.py                    Ranking estructural e inyección
  dream.py                       Dream fase 1: modelo local, agrupación estructural
  schedule.py                    Scheduler pluggable: launchd | systemd | loop
  bench.py                       Runner de M4: lee los umbrales, nunca los fija
  simulate.py                    Ensayo end-to-end. Nunca toca el store real
  cli.py                         init | status | why | export | audit | dream | schedule | doctor | …
tests/                         Tests unitarios y el round trip captura→export→validar
tools/                         El gate: lint-docs, lint-code, validate-schema
doc/00-spec.md                 Spec v0.3 (prosa normativa)
doc/PLAN-v0.3.md               Alcance de referencia
doc/adr/ADR-001-…              Por qué no competimos con Auto Dream
doc/adr/ADR-002-verify-gate.md Qué cuenta como reproducción
schema/trajectory.v1.json      Esquema versionado de Trajectory (modelo de datos normativo)
schema/examples/               Fixtures válidas e inválidas
bench/PREREG.md                Benchmark pre-registrado, umbrales congelados antes de M1
bench/fixtures/familia-a|c|d/  Los repos fixture de M4 (falta congelar identificadores)
bench/fixtures/selftest/       Fixtures sintéticos del gate del runner. NO son los de M4
doc/HANDOFF.md                 Handoff de control: estado, reglas y la cola de trabajo
LATER.md                       Todo lo diferido a propósito, con el motivo
```

## Milestones

| M | Entrega | Gate |
|---|---|---|
| M0 ✅ | Docs: spec v0.3, ADR-001, ADR-002, esquema versionado, PREREG, README | `make check` pasa ✅ · la revisión de ADR-001 por Ismael **sigue pendiente** |
| **M1** 🟡 | Capture: `PostToolUse`, `PostToolUseFailure`, `PreCompact`, `Stop`, `SessionEnd` → SQLite. Redactor determinista | Código listo, y el gate ya es un comando: `nightshift audit --min-sessions 5`. Le faltan 5 sesiones reales en el store |
| **M2** 🟡 | Retrieve: inyección estructural en `SessionStart`, y otra vez en el primer prompt clasificado | Código listo. `/nightshift:why` reconstruye la trayectoria origen de cada inyección |
| M3 🟡 | Dream `consolidate` ✅ + scheduler pluggable ✅ | Los dos entregados: `nightshift dream --selftest` pasa y `nightshift schedule status` reporta las últimas corridas. El gate del milestone — **3 noches seguidas sin intervención** — lo corre Matías |
| M4 🟡 | **Benchmark — go/no-go**. Runner ✅ | Mejora ≥ umbral pre-registrado en ≥ 2 de A/C/D, cero regresión frente a S0. El runner está y **se niega a correr**: `bench/PREREG.md` sigue en borrador con 19 `TODO(Matias)` |
| M5 | Dream `verify` (worktree efímero + gate). **Sólo si M4 pasa** | Precisión de `procedure` > `candidate` en re-corrida del benchmark |
| M6+ | Adapter de OpenCode, marketplace de plugins, Omarchy/Quattro | Ver [`LATER.md`](LATER.md) |

M5 va después de M4 a propósito: `verify` es lo más caro de construir y sólo vale la
pena si la memoria procedimental cruda ya muestra ganancia.

## Correr el gate

```sh
make check            # todo lo de abajo
make lint-docs        # estructura de la documentación y enlaces internos
make lint-code        # stdlib pura, sin red, coexistencia con Auto Memory, plugin bien formado
make validate-schema  # los válidos validan Y los inválidos son rechazados
make test             # tests unitarios (unittest de la stdlib)
make selftest         # replay de los siete hooks contra un store desechable
make dream-selftest   # el gate de M3-a. Necesita modelo local, por eso NO está en check
make bench-selftest   # el gate del runner de M4 (fixtures sintéticos, no el benchmark)
make bench-fixtures   # cada tarea falla antes y la resuelve su fix de referencia
make bench-check      # qué le falta al pre-registro para poder correr M4
make simulate         # el ensayo end-to-end (no cierra ningún gate — ver arriba)
```

`make check` es el gate. No necesita dependencias más allá de
[`check-jsonschema`](https://github.com/python-jsonschema/check-jsonschema) para el paso
del esquema, y cae a `uvx` o `pipx` si no está en el `PATH`.

### Auditar lo que quedó guardado

`nightshift audit` es el gate de M1 hecho script. Recorre cada cadena persistida en el
store y afirma que ninguna matchea un patrón de `deny_paths`, que ninguna matchea una
regla de secreto del redactor, que no sobrevivió ninguna ruta absoluta del home, que no
entró nada del árbol de Auto Memory, y que ningún `abstraction.pattern` lleva una ruta.
Sale 1 ante cualquier hallazgo, o con menos sesiones que `--min-sessions`.

```sh
nightshift audit                    # sólo los chequeos de fuga
nightshift audit --min-sessions 5   # el gate de M1: fugas Y cinco sesiones reales
nightshift audit --json             # el mismo reporte, legible por máquina
```

El reporte dice **dónde** (trayectoria, paso, campo) y **qué regla** saltó — nunca el
valor. Un reporte que cita la fuga la propaga a la terminal, al scrollback y al pipe de
quien lo corrió.

### Dream fase 1 — `consolidate`

`nightshift dream` agrupa las trayectorias cerradas por tipo de tarea, le pide al modelo
**local** el patrón estructural de cada grupo, y deja el resultado en `candidate` con su
`abstraction` y su `valid_when`. Si una trayectoria nueva contradice una vieja, la vieja
pasa a `superseded` enlazada a su sucesora — **no se borra nunca**.

```sh
nightshift dream              # consolidar los últimos 7 días
nightshift dream --dry-run    # mostrar qué haría, sin escribir
nightshift dream --selftest   # el gate de M3-a, sobre un set fixture desechable
```

El modelo corre local — Qwen por `subprocess`, autodetectado desde ollama, el más chico
ya descargado, y nunca se baja nada solo. **Si no hay modelo local, dream falla y lo
dice** (sale 2): no hay fallback remoto ni heurística que finja ser consolidación. Salir
1 significa que había material y no salió nada.

Todo lo que produce el modelo pasa por los mismos gates que la captura: el esquema
rechaza rutas en `abstraction.pattern`, el redactor rechaza identificadores del repo y el
auditor de M1 rechaza fugas. Una respuesta rechazada se reintenta, y un grupo que insiste
se descarta: si el modelo produce algo que no valida, el bug es del prompt, no del
esquema.

Una `candidate` **no** está verificada. Se inyecta con menos peso y marcada como no
verificada, porque `verify` (M5) está bloqueado hasta el veredicto de M4.

### Programar la corrida nocturna

```sh
nightshift schedule status              # backend, qué hay instalado y las últimas corridas
nightshift schedule install --dry-run   # mostrar la unidad, sin escribir nada
nightshift schedule install             # escribirla y cargarla
nightshift schedule uninstall
```

Tres backends detrás de una interfaz: `launchd` (macOS, target primario), `systemd`
(timer de **usuario**, nunca unidad de sistema) y `loop` (`nightshift schedule loop`, en
primer plano, para desarrollo). El backend se autodetecta salvo que `scheduler_backend`
diga otra cosa. En macOS el job corre bajo `caffeinate -s`: un equipo que se duerme a
mitad de la consolidación no la termina.

Escribir la unidad y cargarla son pasos distintos a propósito — `--dry-run` la muestra sin
escribirla, `--no-activate` la escribe sin cargarla en el gestor del sistema.

Cada corrida de dream queda registrada, y `schedule status` imprime las últimas con su
código de salida. Ese es el punto: un scheduler sin corridas registradas es una promesa,
no un hecho. El gate de M3 son tres noches seguidas sin intervención, lo corre una
persona, y esto es lo que lo hace verificable.

### Ensayar todo junto

```sh
nightshift simulate              # sesiones sintéticas por los hooks reales
nightshift simulate --no-model   # saltar dream, para máquinas sin modelo local
```

Corre siete sesiones sintéticas por los siete hooks —incluida una que muere sin
`SessionEnd`, una que toca un `deny_path` y otra que lleva un secreto—, después audita el
store, verifica que la huérfana quedó cerrada, que el retrieval corrió en las dos pasadas,
consolida con el modelo local, instala el scheduler en un `HOME` temporal, corre tres
noches simuladas y vuelve a auditar. Todo en un store desechable.

**No es evidencia para el gate de M1 ni para el de M3.** M1 pide cinco sesiones *reales*;
M3, tres *noches sin intervención*. Una sesión sintética no es una sesión real y tres
corridas en un bucle no son tres noches: no hay suspensión, ni batería, ni un launchd que
se olvidó de disparar, que es justamente lo que esos gates miden. Por eso el ensayo nunca
escribe en el store real: un gate de sesiones reales no se cierra inventando sesiones.

### El runner del benchmark de M4

El runner está construido. **No puede correr**, y ése es el punto:

```sh
nightshift bench check      # qué le falta al pre-registro (hoy sale 1)
nightshift bench plan --fixture <f>   # la grilla del experimento: planificar no es correr
nightshift bench run  --fixture <f> --agent "<cmd>"   # sale 3 mientras PREREG esté abierto
nightshift bench selftest   # el gate del propio runner, con fixtures sintéticos
```

Los tres repos fixture están construidos —`bench/fixtures/familia-{a,c,d}/`— y
`nightshift bench fixtures` (`make bench-fixtures`) afirma tarea por tarea que **el gate
falla antes y lo resuelve el fix de referencia**. Un fixture donde una tarea ya pasa, o
donde ninguna resolución es posible, no mide nada y no rompe nada: es la forma más
silenciosa de tener un benchmark que no mide. La familia A son diez bugs con una sola
causa; la C, dos repos con el mismo patrón estructural y cero vocabulario compartido; la D
trae ground truth hecho a mano y un clasificador determinista.

El adaptador que lanza el agente en cada celda vive en `bench/agentes/` y **se niega a
correr por el mismo motivo que el runner**: sin el modelo, el límite de tool calls y el
protocolo de reset —los tres `TODO(Matias)`— no elige valores por su cuenta.

`bench/PREREG.md` dice **BORRADOR — no congelado** y tiene 19 `TODO(Matias)`. Hasta que
una persona lo congele, `bench run` se niega y lista qué falta, con sección y línea. Un
umbral que se ajusta después de ver el resultado no es un umbral, y un runner que corre
con el pre-registro abierto es la forma más cómoda de ajustarlo sin darse cuenta.

Dos reglas más que el runner se aplica a sí mismo: **indecidible no es go** — si falta un
umbral o falta una familia no hay veredicto, en vez de uno favorable — y **no hay juicio
de modelo en ningún punto**: la resolución es el gate del fixture (sale 0 ahora, salía ≠ 0
antes) y la clasificación falsa/stale de la familia D la hace el script determinista del
propio fixture.

`make doctor` va aparte a propósito: chequea *tu* instalación (config presente, captura
activa), que no es algo que CI tenga por qué afirmar.

## Reglas de trabajo

Están en [`CLAUDE.md`](CLAUDE.md). En corto: un milestone por rama; el gate es un
script, no un juicio; cada sesión termina en commit medible o el motivo va a
`LATER.md`; Claude Code lee los umbrales del benchmark, nunca los fija.

## Licencia

Apache-2.0. Ver [LICENSE](LICENSE) y [NOTICE](NOTICE).
