# LATER

Todo lo que se difirió a propósito, con el motivo. Un ítem sin motivo no pertenece a
este archivo: o se hace, o se descarta.

Regla de §5 del plan: si una sesión no termina en commit medible, el motivo se anota
acá.

---

## Deuda de procedencia

**La spec v0.2 no está en el repositorio.** Este repo se creó en el commit de M0.
La v0.2 vivía como documento de trabajo fuera del repo y no se importó, así que
`doc/00-spec.md` v0.3 **reconstruye** la estructura de v0.2 y le aplica los siete
cambios de §1 del plan. Las secciones marcadas *(sin cambio respecto a v0.2)* son
reconstrucción de buena fe, no citas literales.

Consecuencia: el changelog de §12 de la spec es fiel a *lo que el plan pidió cambiar*,
pero no puede ser fiel a *lo que la v0.2 decía exactamente*.

**Acción pendiente:** si el documento v0.2 existe en algún lado, importarlo como
`doc/archive/00-spec-v0.2.md` y reconciliar. Si no existe, borrar esta sección y
declarar la v0.3 como origen. **Decide Matías.**

---

## Diferido hasta M1 (Capture)

| Ítem | Motivo |
|---|---|
| DDL de SQLite | El esquema JSON es normativo; el mapeo a tablas depende de cómo consulte el retrieval, y eso no se sabe hasta M2. Se define en M1 y se re-mira en M2. |
| Formato del archivo de config de `deny_paths` | Debe existir **antes** del primer hook (spec §8.1), pero el formato concreto no es una decisión de M0. |
| Lista de reglas del redactor determinista | Se deriva de las fixtures de Histora, que no están en este repo. |
| Fixtures de Histora para los tests del redactor | Material sensible. No entran a este repo: viven fuera y el test las toma por path configurable. |
| Protocolo daemon ↔ hook (socket, timeouts) | Detalle de implementación. Lo único normativo hoy es §7.2: si el daemon no responde, el hook sale 0 y no bloquea. |
| Re-verificación del formato de hooks | Los nombres se verificaron el 2026-08-26 contra `code.claude.com/docs/en/hooks`. Cambian entre versiones: M1 re-verifica y actualiza spec §5.4 con fecha. |
| Vocabulario normalizado de tools | `read_file`/`edit_file`/`write_file`/`run_shell`/`search`/`fetch`/`other` es un primer corte. Se cierra con datos reales de captura, no por adivinanza. |

## Diferido hasta M2 (Retrieve)

| Ítem | Motivo |
|---|---|
| Cómo se elige `N` (procedimientos inyectados por sesión) | Depende del presupuesto de contexto real, que se mide en M2. |
| Función de ranking y peso exacto de `candidate` vs `procedure` | Spec §6.3 fija el orden (candidate < procedure); el número sale de datos. |
| Cómo se usa `MEMORY.md` como señal de retrieval | Está permitido leerlo (spec §1.3.4). Qué señal se extrae exactamente se decide con memoria nativa real delante. |
| `/nightshift status|dream|why` como plugin vs slash commands sueltos | El formato de plugin de Claude Code cambia. Se elige en M2, no antes. |

## Diferido hasta M3 (Dream + scheduler)

| Ítem | Motivo |
|---|---|
| Modelo Qwen concreto y tamaño | Depende de lo que corra decentemente en la Air durante la ventana nocturna. |
| Política de retención del store | No hay volumen real todavía. Decidir con datos, no con intuición. |

## Diferido hasta M4 (Benchmark)

| Ítem | Motivo |
|---|---|
| Todos los `TODO(Matias)` de `bench/PREREG.md` | **Claude Code no fija umbrales** (plan §5). Los resuelve una persona antes de congelar. |
| Repos fixture de las familias A y C | Se construyen en M1; los identificadores se congelan en PREREG antes de M4. |
| Tratamiento estadístico con n=3 por celda | Hay que decidir y escribirlo antes de congelar, incluyendo reconocer el poder estadístico disponible. |
| Protocolo de reset de Auto Dream entre corridas | Amenaza a la validez identificada, mitigación sin resolver (PREREG §5). |

## Diferido hasta M5 (Verify) — **bloqueado por el veredicto de M4**

| Ítem | Motivo |
|---|---|
| Presupuesto de verify por noche | Cada verify consume worktree y CPU. Sin datos de M3 no hay número sensato. |
| Caducidad de `procedure` cuando el repo avanza | ¿Un procedimiento verificado sobre un commit viejo sigue valiendo? Abierto en ADR-002. |
| Registro/formato de gates del usuario | ADR-002 fija *qué* es un gate (comando, exit code). *Cómo* se declara es de M5. |

**Prohibido empezar M5 antes del veredicto de M4** (plan §5).

## Diferido a M6+ — fuera de alcance de v0.3

| Ítem | Motivo |
|---|---|
| Adapter de OpenCode | Prohibido abrirlo (plan §5). La *abstracción* ya es cross-harness por diseño (spec §4.4) para que el adapter no requiera migración de datos, pero el adapter no se toca. |
| Publicación en el marketplace de plugins de Claude Code | Distribuir antes de tener el veredicto de M4 es vender algo que quizá se congele. |
| Omarchy / Quattro | Fuera de alcance de v0.3. |
| Sincronización remota / multi-máquina / multi-usuario | Contradice "sin dependencias de API remota" y multiplica la superficie de privacidad. |

---

## Decisiones que necesitan a una persona

1. **Umbrales de `bench/PREREG.md`.** Todos los `TODO(Matias)`. Bloquean el
   congelamiento del pre-registro, que a su vez bloquea M1.
2. **Revisión de ADR-001 por Ismael.** Es el gate humano de M0. Las cuatro preguntas
   concretas están al final del ADR.
3. **Deuda de procedencia de la v0.2** (arriba).
4. **Visibilidad del repositorio.** Se creó privado. Pasar a público es una decisión de
   Matías, no del agente.
