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

Para iterar sobre el plugin mismo, editá y corré `/reload-plugins` — los cambios en los
hooks y en `nightshift/*.py` no tienen efecto hasta que lo hagas.

### Skills

| Skill | Qué hace |
|---|---|
| `/nightshift:status` | Qué hay capturado y qué se inyectó en esta sesión |
| `/nightshift:why <id>` | Reconstruye la trayectoria origen de una inyección — el gate de M2 |
| `/nightshift:doctor` | Chequeo de invariantes en runtime más un replay end-to-end de los siete hooks |
| `/nightshift:dev` | Estado de desarrollo del plugin, para las sesiones que lo modifican |

`/nightshift:dream` todavía no existe: llega con M3 (`consolidate`) y M5 (`verify`).

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
skills/                        /nightshift:status | why | doctor | dev
nightshift/                    La implementación. Sólo librería estándar
  config.py                      Rutas, deny_paths, el guard de escritura de Auto Memory
  redact.py                      Redactor determinista — corre antes de persistir
  store.py                       SQLite; export_trajectory() emite trajectory.v1
  context.py                     Fingerprint del repo, clasificación de tarea, normalización
  hook.py                        Despacho de hooks. Nunca levanta, siempre sale 0
  retrieve.py                    Ranking estructural e inyección
  cli.py                         init | status | why | export | doctor | selftest | dev
tests/                         Tests unitarios y el round trip captura→export→validar
tools/                         El gate: lint-docs, lint-code, validate-schema
doc/00-spec.md                 Spec v0.3 (prosa normativa)
doc/PLAN-v0.3.md               Alcance de referencia
doc/adr/ADR-001-…              Por qué no competimos con Auto Dream
doc/adr/ADR-002-verify-gate.md Qué cuenta como reproducción
schema/trajectory.v1.json      Esquema versionado de Trajectory (modelo de datos normativo)
schema/examples/               Fixtures válidas e inválidas
bench/PREREG.md                Benchmark pre-registrado, umbrales congelados antes de M1
LATER.md                       Todo lo diferido a propósito, con el motivo
```

## Milestones

| M | Entrega | Gate |
|---|---|---|
| M0 ✅ | Docs: spec v0.3, ADR-001, ADR-002, esquema versionado, PREREG, README | `make check` pasa ✅ · la revisión de ADR-001 por Ismael **sigue pendiente** |
| **M1** 🟡 | Capture: `PostToolUse`, `PostToolUseFailure`, `PreCompact`, `Stop`, `SessionEnd` → SQLite. Redactor determinista | Código listo. 5 sesiones reales capturadas sin fuga de `deny_paths` (test automatizado sobre el dump) |
| **M2** 🟡 | Retrieve: inyección estructural en `SessionStart` | Code done. `/nightshift:why` reconstruye la trayectoria origen de cada inyección |
| M3 | Dream `consolidate` + scheduler pluggable (`launchd`/`systemd`/`loop`) | 3 noches seguidas sin intervención |
| M4 | **Benchmark — go/no-go** | ≥ umbral pre-registrado en ≥ 2 de A/C/D, cero regresión frente a S0 |
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
```

`make check` es el gate. No necesita dependencias más allá de
[`check-jsonschema`](https://github.com/python-jsonschema/check-jsonschema) para el paso
del esquema, y cae a `uvx` o `pipx` si no está en el `PATH`.

`make doctor` va aparte a propósito: chequea *tu* instalación (config presente, captura
activa), que no es algo que CI tenga por qué afirmar.

## Reglas de trabajo

Están en [`CLAUDE.md`](CLAUDE.md). En corto: un milestone por rama; el gate es un
script, no un juicio; cada sesión termina en commit medible o el motivo va a
`LATER.md`; Claude Code lee los umbrales del benchmark, nunca los fija.

## Licencia

Apache-2.0. Ver [LICENSE](LICENSE) y [NOTICE](NOTICE).
