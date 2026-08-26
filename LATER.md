# LATER

Todo lo que se difirió a propósito, con el motivo. Un ítem sin motivo no pertenece a
este archivo: o se hace, o se descarta.

Regla de §5 del plan: si una sesión no termina en commit medible, el motivo se anota
acá.

---

## Deuda de proceso: se pasó de M0 sin cerrar su gate

M0 tenía dos gates: `make check` (script) e **Ismael revisa ADR-001** (humano). El
primero pasa. El segundo **nunca ocurrió**, y aun así se implementaron M1 y M2 a pedido
explícito de Matías.

Por qué importa y no es burocracia: ADR-001 es el documento que decide *contra qué no
competimos*. Si la revisión encuentra que alguna de las cinco capacidades es "todavía no
lo hicieron" y no "por diseño", esa capacidad sale del roadmap — y M1/M2 ya están
construidos sobre las cinco. El costo de descubrirlo tarde es código escrito, no sólo
tiempo de lectura.

**Acción pendiente:** la revisión de ADR-001 sigue siendo el gate de M0. Si cambia
alguna fila de la matriz, hay que revisar qué parte de la captura sobra.

---

## Diferido: el daemon

La spec §3.1 describe un `nightshiftd`. M1+M2 escriben directo a SQLite (WAL) y no hay
daemon.

Motivo: el daemon existía para amortizar la carga del modelo local, y capturar no usa
modelo. Meterlo ahora sería un proceso de fondo más que puede colgarse, en contra de
§7.2 ("nightshift jamás debe bloquear una sesión"). Se reabre con M3, que sí carga Qwen.

Costo asumido: cada hook paga el arranque de un intérprete Python. Si eso se nota en
sesiones con muchas tool calls, el daemon deja de ser diferible. **Sin medir todavía.**

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
| ~~DDL de SQLite~~ | **Hecho** en `nightshift/store.py`. El contrato público sigue siendo `export_trajectory()`, que valida contra el esquema de M0. |
| ~~Formato de la config de `deny_paths`~~ | **Hecho**: `~/.nightshift/config.json`, creado por `nightshift init`. Sin él no se captura. |
| Lista de reglas del redactor determinista | Se deriva de las fixtures de Histora, que no están en este repo. |
| Fixtures de Histora para los tests del redactor | Material sensible. No entran a este repo: viven fuera y el test las toma por path configurable. **El redactor tiene tests con fixtures sintéticas, no con las de Histora.** El gate de M1 no está cerrado hasta que corra contra ellas. |
| El gate de M1: 5 sesiones reales sin fuga | **El comando está** (`nightshift audit --min-sessions 5`, T1) y sobre el store real **no encuentra ninguna fuga**. Lo que falta es uso: hay 3 sesiones distintas capturadas de las 5 que pide el gate. Se cierra usando el plugin, no escribiendo código. |
| Fugas fuera del alcance de `audit` | `audit` afirma sobre lo **persistido**: rutas, secretos, home, árbol de Auto Memory, `abstraction.pattern`. No puede afirmar sobre lo que nunca se guardó ni sobre el *contenido* de un archivo negado que hubiera entrado sin su ruta. Que un `deny_path` no se capture lo defiende el redactor y sus tests, no el auditor. |
| `audit` no distingue mención de ruta más allá del separador | Un token cuenta como ruta si tiene `/`; `.env` suelto en un comentario es una mención. La regla es explicable y está testeada en los dos sentidos, pero es una heurística: una fuga escrita sin barras (`env`, `id_rsa`) no la ve. |
| Protocolo daemon ↔ hook (socket, timeouts) | Sin daemon todavía (ver arriba). Lo normativo se cumple: el hook sale 0 pase lo que pase. |
| Re-verificación del formato de hooks | Los nombres se verificaron el 2026-08-26 contra `code.claude.com/docs/en/hooks`. Cambian entre versiones: M1 re-verifica y actualiza spec §5.4 con fecha. |
| Vocabulario normalizado de tools | Implementado como primer corte en `context.TOOL_MAP`. **Todo lo que no está mapeado cae a `other`, incluidas todas las tools MCP.** Se cierra con datos reales de captura, no por adivinanza. |
| Heurística de `task_type` | `context.TASK_TYPE_RULES` es un regex por clase, orden fijo, primera que matchea. Funciona en español e inglés y está testeada, pero es una adivinanza informada: hay que revisarla contra trayectorias reales. |
| Heurística de señal decisiva | Hoy: todo `tool_failure` es decisivo, y un comando de test que pasa también. Es lo bastante bueno para M2 y probablemente demasiado generoso. |
| `hypothesis` nunca se puebla | Extraerla exigiría guardar texto del prompt, que se decidió no persistir. Queda para dream (M3), que sí puede derivarla de la trayectoria. |

## Diferido hasta M2 (Retrieve)

| Ítem | Motivo |
|---|---|
| Dos pasadas de retrieval, dos oportunidades de gastar contexto | T2 inyecta en `SessionStart` (por repo y recencia) y otra vez en el primer prompt clasificado (por tipo). Nunca repite una trayectoria, pero una sesión puede recibir hasta `2 × max_injected`. Si eso resulta caro en contexto, el número que hay que revisar es `max_injected`, no la segunda pasada. **Sin medir.** |
| Cómo se elige `N` | Hoy `max_injected: 3` por config. El número sale de una intuición, no de medir presupuesto de contexto. |
| Los pesos del ranking | `retrieve.W_*` son constantes elegidas a mano. Son deterministas y auditables (`why` los reimprime), pero nadie las calibró. M4 es quien puede decir si sirven. |
| Ventana de las huérfanas | `orphan_after_hours: 12` es un default razonado, no medido: por debajo, una sesión inactiva pero viva (una que quedó abierta durante la noche) se cierra y la siguiente tool call abre una trayectoria nueva; por encima, una sesión muerta tarda más en volverse recuperable. Se ajusta con trayectorias reales delante. |
| Una máquina suspendida cuenta como inactividad | El barrido mira el reloj de pared, no el tiempo de CPU. Un portátil cerrado toda la noche con una sesión abierta la ve como huérfana a la mañana. Cerrarla no borra nada, pero parte la sesión si el usuario la retoma. |
| Retención y tamaño del store | Sin política. Una trayectoria por sesión y hasta 400 pasos cada una crece sin techo. |
| Función de ranking y peso exacto de `candidate` vs `procedure` | Spec §6.3 fija el orden (candidate < procedure); el número sale de datos. |
| Cómo se usa `MEMORY.md` como señal de retrieval | Hoy sólo se detecta **si existe**, y si existe el texto inyectado lo dice. No se lee el contenido. Qué señal extraer se decide con memoria nativa real delante. |
| Transferencia cross-repo de verdad | `cross_repo` sigue **apagado** por defecto, pero el camino ya es correcto: sólo cruzan trayectorias con `abstraction` (que ahora produce dream) y de ellas se emite **sólo** el patrón, nunca los pasos. Falta la decisión de encenderlo y la evidencia de M4 de que transferir sirve. La capacidad C no está entregada. |
| ~~Plugin vs slash commands sueltos~~ | **Resuelto**: plugin. Las skills quedan namespaced como `/nightshift:<skill>`, no `/nightshift <sub>` como suponía el plan. Spec §5.5 enmendada. |

## Diferido hasta M3 (Dream + scheduler)

| Ítem | Motivo |
|---|---|
| Modelo Qwen concreto y tamaño | **Sin medir.** La autodetección toma el qwen más chico ya descargado (acá `qwen3.5:4b`) porque el target es una Air de noche. Con 4b los patrones salen genéricos: sirven para el gate estructural, no está probado que sirvan para el benchmark. Qué modelo usar en M4 se decide midiendo. |
| Calidad del prompt de `consolidate` | El prompt de `dream.PROMPT` es una primera versión. Los gates que lo rodean (esquema, redactor, auditor) están testeados; que lo que produce sea *útil* no lo prueba ningún test — lo prueba M4. |
| Agrupación fina | Hoy se agrupa por tipo de tarea y nada más, porque agrupar por firma de herramientas dejaba grupos de uno. Con volumen real habrá que agrupar mejor: un `debug_test_failure` de decodificación y uno de import circular no comparten patrón, y hoy caen en el mismo grupo. |
| Una candidata por grupo y por corrida | Se promueve el representante del grupo; el resto queda `closed` y sigue siendo recuperable como cruda. Si el grupo tenía dos patrones distintos, el segundo se pierde hasta la próxima corrida. |
| Peso de inyección de `candidate` (0.6) | Elegido a mano, como los pesos del ranking. Spec §6.3 fija el orden (`candidate` < `procedure`), no el número. |
| `dream` no puebla `hypothesis` | Sigue vacía: el modelo produce `abstraction`, no hipótesis por trayectoria. Se puede derivar, no se hizo. |
| Las tres noches del gate de M3 | El scheduler está y `schedule status` reporta las corridas. **La evidencia no está**: hay que instalar el timer en la Air y dejarlo correr tres noches. Lo hace una persona, no un agente. |
| Ventana horaria fija (03:30) | Config, pero elegida a mano. No hay medición de cuánto tarda una consolidación real ni de si entra en la ventana de batería. |
| `schedule status` no dice cuándo es la próxima corrida | `launchctl print` y `systemctl list-timers` lo saben; nightshift no los consulta todavía. Lo que sí muestra es lo que pasó, que es lo que el gate necesita. |
| El backend `loop` no sobrevive a un reinicio | Es el backend de desarrollo, corre en primer plano y muere con la terminal. Documentado, no arreglado: para eso están los otros dos. |
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
4. **Visibilidad del repositorio.** Pasar a público es una decisión de Matías, no del
   agente.
5. **Correr el gate real de M1.** El test sobre el dump ya existe y es
   `nightshift audit --min-sessions 5`; hoy sale 1 sólo por el conteo de sesiones (3 de
   5), sin ninguna fuga. Falta usar el plugin en dos sesiones reales más. Hasta que eso
   pase, M1 es código sin evidencia suficiente.
