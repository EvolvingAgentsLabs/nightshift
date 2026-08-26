# nightshift

**Una capa de memoria procedimental sobre la memoria declarativa nativa del agente.**

*[Read this in English](README.md)*

> **Estado: M0 — sólo documentación.** Todavía no hay código en este repositorio, y es
> deliberado. La spec, los dos ADRs, el esquema versionado de trayectoria y el
> benchmark pre-registrado se cierran antes de escribir el primer hook. Ver
> [Milestones](#milestones).

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

## Estructura del repositorio

```
doc/00-spec.md                 Spec v0.3 (prosa normativa)
doc/PLAN-v0.3.md               Alcance de referencia
doc/adr/ADR-001-…              Por qué no competimos con Auto Dream
doc/adr/ADR-002-verify-gate.md Qué cuenta como reproducción
schema/trajectory.v1.json      Esquema versionado de Trajectory (modelo de datos normativo)
schema/examples/               Fixtures válidas e inválidas — el gate de M0
bench/PREREG.md                Benchmark pre-registrado, umbrales congelados antes de M1
LATER.md                       Todo lo diferido a propósito, con el motivo
```

## Milestones

| M | Entrega | Gate |
|---|---|---|
| **M0** | Docs: spec v0.3, ADR-001, ADR-002, esquema versionado, PREREG, README | `make check` pasa **y** Ismael revisa ADR-001 |
| M1 | Capture: `PostToolUse`, `PostToolUseFailure`, `PreCompact`, `Stop` → SQLite. Redactor determinista | 5 sesiones reales capturadas sin fuga de `deny_paths` (test automatizado sobre el dump) |
| M2 | Retrieve: inyección estructural en `SessionStart` | `/nightshift why` reconstruye la trayectoria origen de cada inyección |
| M3 | Dream `consolidate` + scheduler pluggable (`launchd`/`systemd`/`loop`) | 3 noches seguidas sin intervención |
| M4 | **Benchmark — go/no-go** | ≥ umbral pre-registrado en ≥ 2 de A/C/D, cero regresión frente a S0 |
| M5 | Dream `verify` (worktree efímero + gate). **Sólo si M4 pasa** | Precisión de `procedure` > `candidate` en re-corrida del benchmark |
| M6+ | Adapter de OpenCode, marketplace de plugins, Omarchy/Quattro | Ver [`LATER.md`](LATER.md) |

M5 va después de M4 a propósito: `verify` es lo más caro de construir y sólo vale la
pena si la memoria procedimental cruda ya muestra ganancia.

## Correr el gate de M0

```sh
make check          # lint-docs + validate-schema
make lint-docs      # estructura, enlaces, límites de M0
make validate-schema
```

`validate-schema` necesita [`check-jsonschema`](https://github.com/python-jsonschema/check-jsonschema).
Si no está en el `PATH`, el script cae a `uvx` o `pipx`.

## Reglas de trabajo

Están en [`CLAUDE.md`](CLAUDE.md). En corto: un milestone por rama; el gate es un
script, no un juicio; cada sesión termina en commit medible o el motivo va a
`LATER.md`; Claude Code lee los umbrales del benchmark, nunca los fija.

## Licencia

Apache-2.0. Ver [LICENSE](LICENSE) y [NOTICE](NOTICE).
