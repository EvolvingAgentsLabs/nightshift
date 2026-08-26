# nightshift — Plan v0.3

> Documento de entrada, pegado tal cual lo escribió Matías. Es la fuente de verdad
> del alcance de v0.3. La spec (`doc/00-spec.md`) es su desarrollo; si divergen,
> gana este plan y la spec se corrige.

Delta respecto a spec v0.2. Cambia la tesis, el baseline y el orden de milestones. No cambia el stack (daemon Python, hooks en PATH, scheduler pluggable, Qwen local) ni la disciplina (gates before results, tests before code, LATER.md).

## 0. Tesis (reescrita)

Claude Code ya trae Auto Memory (notas declarativas por repo) y Auto Dream (consolidación en background). nightshift **no compite en "notas + sueño"**. Compite en cuatro cosas que lo nativo no puede hacer por diseño:

| # | Capacidad | Nativo | nightshift |
|---|-----------|--------|------------|
| A | Memoria procedimental: trayectorias causales (hipótesis → tools → señal decisiva → fix) | No. Guarda hechos | Sí. CTE capture |
| B | Alternativas descartadas con precondiciones | No. Auto Dream borra lo contradicho | Sí. Nodo `superseded_by` + `valid_when` |
| C | Cross-repo / cross-harness | No. Sellado por repo | Sí. Abstracción de trayectoria + `deny_paths` |
| D | Consolidación verificable: una trayectoria pasa a procedimiento solo si reproducirla pasa un gate | No. Juicio del modelo | Sí. Dream gated por verifiers del usuario |
| E | Captura pre-`/compact` del razonamiento intermedio | No | Sí. Hook PreCompact |

Si M4 no muestra ganancia medible en A, C y D frente a **Auto Memory + Auto Dream encendidos**, el proyecto se congela como spec.

## 1. Cambios obligatorios a la spec

- §1.1 Positioning: "procedural memory layer over the agent's native declarative memory". Nunca "reemplaza" Auto Memory.
- §1.3 condición 2: install-to-first-injected-strategy < 10 min en macOS o Linux, cero API keys nuevas. Sin cambio.
- §1.3 condición nueva 4: **coexistencia** — nightshift nunca escribe en `~/.claude/projects/*/memory/`. Lee MEMORY.md solo como señal de retrieval.
- §4 Data model: agregar `Trajectory.abstraction` (patrón sin paths ni nombres de repo), `Trajectory.valid_when`, `Trajectory.superseded_by`, `Trajectory.verified: {gate_id, passed_at, run_id}`.
- §6 Dream: dos fases. `consolidate` (como v0.2) y `verify` (nuevo): re-ejecuta la trayectoria en un worktree efímero contra el gate declarado; solo lo verificado se promueve a `procedure`. Trayectorias no verificables quedan `candidate` y se inyectan con menor peso.
- §7.1 Scheduler pluggable (`launchd | systemd | loop`) requisito de M3.
- §8 Privacy: `deny_paths` obligatorio antes del primer hook. Abstracción cross-repo pasa por un redactor determinista (regex + lista de identificadores del repo) antes de persistir. Histora primero.
- §10 Benchmark: baseline S0 pasa de "sin memoria" a "Claude Code con Auto Memory + Auto Dream on".

## 2. Hooks (Claude Code)

| Hook | Acción |
|------|--------|
| `SessionStart` | Retrieve por estructura (tipo de tarea + señales del repo), inyectar ≤ N procedimientos verificados como contexto adicional. Loguear qué se inyectó. |
| `PostToolUse` | Capturar (tool, args redactados, resultado resumido, Δ estado) → append a trayectoria activa. |
| `PreCompact` | Snapshot de la trayectoria activa completa antes de que muera el contexto. |
| `Stop` | Cerrar trayectoria: outcome (tests pasaron / usuario corrigió / abandonada), gate asociado si existe. |
| `UserPromptSubmit` | Solo detectar correcciones ("no, eso está mal") → marcar el nodo anterior como `contradicted`. |

Comandos: `/nightshift status`, `/nightshift dream [--verify]`, `/nightshift why <procedure_id>` (muestra la trayectoria origen — auditabilidad es feature, no debug).

Verificar en la doc actual de Claude Code los nombres exactos de hooks y el formato de plugin; cambian.

## 3. Milestones (reordenados)

**M0 — Docs (sin código).** Spec v0.3, ADR-001 "por qué no competir con Auto Dream", ADR-002 "verify gate: qué cuenta como reproducción", esquema JSON de Trajectory versionado, matriz de la sección 0 en el README. Gate: Ismael revisa ADR-001.

**M1 — Capture.** Hooks `PostToolUse`, `PreCompact`, `Stop` escribiendo a SQLite local. Redactor determinista con tests contra fixtures de Histora. Gate: 5 sesiones reales tuyas capturadas sin fuga de `deny_paths` (test automatizado sobre el dump).

**M2 — Retrieve.** Inyección en `SessionStart` por estructura. Sin dream todavía: inyecta trayectorias crudas recientes del mismo tipo de tarea. Gate: `/nightshift why` reconstruye la trayectoria origen de cada inyección.

**M3 — Dream + scheduler.** `consolidate` con Qwen local, `launchd`/`systemd`/`loop`. Gate: corre 3 noches seguidas sin intervención en la Air (caffeinate + cargador).

**M4 — Benchmark (go/no-go).** Ver sección 4. Gate: mejora ≥ umbral pre-registrado en al menos dos de A/C/D, cero regresión en S0.

**M5 — Verify.** Dream fase 2: reproducción en worktree contra gate. Solo si M4 pasa. Gate: precisión de procedimientos verificados > candidatos en re-corrida del benchmark.

**M6+ (LATER.md):** OpenCode adapter, plugin marketplace de Claude Code, Omarchy/Quattro.

M5 va después de M4 a propósito: verify es lo más caro y solo vale si la memoria procedimental cruda ya muestra ganancia.

## 4. Benchmark M4 (pre-registrar antes de M1)

Tres familias de tareas, cada una mapeada a una capacidad de la matriz:

- **A — Bug recurrente variado.** 10 bugs con causa compartida pero síntoma distinto, en un repo fixture. Métrica: tasa de resolución y tool calls hasta fix.
- **C — Transferencia cross-repo.** Mismo patrón estructural (pipeline con transformaciones opacas) en dos repos distintos. Métrica: resolución en repo B tras aprender en repo A.
- **D — Precisión de consolidación.** Inyectar contradicciones y reversiones; medir cuántas memorias inyectadas son falsas o stale al final. (M5 lo reevalúa con verify.)

Filas: S0 = Claude Code + Auto Memory + Auto Dream on · S1 = S0 + nightshift (candidate only) · S2 = S0 + nightshift (verified, solo tras M5). Mismo modelo, mismo seed de tareas, 3 corridas por celda. Umbrales de go escritos en `bench/PREREG.md` antes de tocar código de M1.

## 5. Reglas de trabajo con Claude Code

- Un milestone por rama. PR solo si el gate pasa; el gate es un script, no un juicio.
- Cada sesión termina en commit medible. Si no hay commit, va a LATER.md el motivo.
- Prohibido: escribir en el directorio de Auto Memory; agregar dependencias de API remota; empezar M5 antes del veredicto de M4; abrir el adapter de OpenCode.
- Claude Code no decide umbrales del benchmark. Los lee de `PREREG.md`.

## 6. Handoff — prompt para pegar en `claude` desde la raíz del repo

```
Lee doc/00-spec.md (v0.2) y este archivo (doc/PLAN-v0.3.md). Tu tarea es M0 únicamente:
1. Producir doc/00-spec.md v0.3 aplicando exactamente los cambios de la sección 1 del plan. No agregues features.
2. Escribir doc/adr/ADR-001-no-competir-con-auto-dream.md y doc/adr/ADR-002-verify-gate.md.
3. Escribir schema/trajectory.v1.json con los campos de §4 del plan, con ejemplos válidos e inválidos en schema/examples/.
4. Escribir bench/PREREG.md con las tres familias y umbrales vacíos marcados TODO(Matias) — no inventes números.
5. Actualizar README.md con la matriz de la sección 0.
Prohibido: escribir código Python, tocar hooks, crear dependencias. Gate de M0: `make lint-docs` pasa y los ejemplos JSON validan contra el schema.
Termina con un resumen de qué quedó en LATER.md.
```
