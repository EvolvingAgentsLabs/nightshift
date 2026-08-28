# LATER

Todo lo que se difirió a propósito, con el motivo. Un ítem sin motivo no pertenece a
este archivo: o se hace, o se descarta.

Regla de §5 del plan: si una sesión no termina en commit medible, el motivo se anota
acá.

---

## Las 5 proyecciones de `cbbd7ff0`, resueltas una por una (2026-08-27)

Primera vez que el ciclo cierra entero sobre el propio repo: dream consolidó la sesión
anterior, **proyectó cinco síntomas que nadie había observado**, y la sesión siguiente fue
a mirarlos contra el código. El veredicto de cada uno, sin redondear:

| # | Proyección (abreviada) | Veredicto |
|---|---|---|
| 1 | Un panel de salud informa cobertura perfecta cuando el denominador es cero | **CONFIRMADA y arreglada.** `_render_sealed` con cero celdas imprimía "la máquina corre entera" y salía 0 |
| 2 | Un bloque de contexto inyectado cita cero ejemplos y pasa el gate porque el gate mira formato y largo | **REFUTADA en el camino vivo.** `retrieve.render` devuelve `""` cuando no eligió nada y el hook no inyecta. El gate que la proyección describe —"ejemplos citados: N"— no existe en el árbol |
| 3 | Una corrida de consolidación queda registrada como exitosa habiendo procesado cero trayectorias | **ABIERTA, y no la cierra un agente.** Es literalmente `PLAN-M4.md` §10 Q6, sin responder. La spec §6.1 dice hoy que `0` significa "consolidó **o** no había nada que consolidar"; si eso está mal, lo decide Matías |
| 4 | Un ensayo end-to-end da verde contra un store vacío | **CONFIRMADA y arreglada.** Es el mismo mecanismo que la 1, y el camino real no necesita ningún archivo roto: `bench run` reemplaza `registros` por `usable_records`, vacío cuando ninguna repetición quedó completa en las dos filas |
| 5 | Un linter de invariantes pasa porque su lista de archivos quedó vacía por un patrón que no matchea nada | **CONFIRMADA como latente, y endurecida.** `pathlib` no expande llaves: `glob("{nightshift,tests}/**/*.py")` devolvía cero archivos y el chequeo de stdlib se apoyaba en el `or` de atrás. No pasaba en vacío hoy; un rename de directorio lo dejaba pasando en vacío sin ruido |

**Dos confirmadas y arregladas, una confirmada como latente y endurecida, una refutada, una
abierta por ser decisión de una persona.** La cuenta se escribe acá y no se redondea en
ningún otro lado: este repo ya se equivocó una vez inflando el puntaje de las proyecciones
(HANDOFF §4-bis), y la forma de que no vuelva a pasar es que haya un solo lugar donde se
cuentan.

Lo que **no** prueba: que idear produzca mejores proyecciones que no idear. Para eso hace
falta el control, y el control es `experimentos/ideate.py` sobre volumen que no hay. Lo
que sí muestra es que el mecanismo produce conjeturas que **se pueden ir a verificar**, y
que verificarlas encontró un defecto real — que es exactamente lo que ADR-004 dijo que
compraba, ahora con n=2.

---

## Lo que el pivot a las tres ideas dejó abierto (2026-08-27)

El pivot está en `doc/HANDOFF.md` §0-bis y `doc/PLAN-M4.md` quedó pausado entero. Lo que
**no** se hizo en la sesión del pivot, con el motivo:

- **La pregunta de M4 sigue sin respuesta.** Nadie midió que recordar *cómo se averiguó*
  algo mejore el trabajo de un agente. El dogfooding no la responde: dice que la máquina
  corre sobre su propio material sin romperse ni filtrar, que es otra cosa. Si el proyecto
  algún día quiere afirmar la primera, necesita M4 o un sustituto, y hoy no tiene ninguno.
- **`make dogfood` no puede verificar la mitad que importa.** El gate afirma sobre el
  store real: gate verde, captura con contenido, sin fugas, trayectorias de este repo. Lo
  que no puede afirmar es que un agente **usó** la memoria inyectada para llegar antes a
  algo. Eso necesita un contrafáctico, que es exactamente lo que M4 era. Se anota como
  límite conocido del gate, no como algo que se olvidó.
- **Las dos paráfrasis que no enganchan siguen sin enganchar.** `resumen`/`memoria
  consolidada`, `métrica`/`contador de cobertura`: es sinónimo, no morfología, y `difflib`
  y el prefijo ya se probaron. Necesita embeddings, que chocan con ADR-003. La enmienda
  0.3.7 no toca esto: cambia el **orden** de lo que engancha, no quién engancha.
- **La regla de orden nueva no está calibrada contra nada, porque no tiene números.**
  `(engancha, score)` es determinista y auditable, pero nadie midió si poner un
  `failure_match` débil por encima de una trayectoria del mismo tipo de tarea con
  desenlace verde ayuda o estorba. Medirlo pide volumen real de sesiones, que es lo mismo
  que le falta a todo lo demás de este repo.
- **La cohorte de captura sigue mezclando generaciones en el promedio.** Sin cambio: no
  lo tocó esta sesión, y sigue anotado más abajo.

**Medido en la sesión del pivot, sobre el store real** (`~/.nightshift`, la única
candidata, `fff6af83`, con sus cuatro proyecciones):

| | resultado |
|---|---|
| paráfrasis de una proyección que enganchan | 4 de 4 |
| control negativo (prompts ajenos) | 0 de 3 |
| lugar de la única fila que engancha, **antes** de la enmienda 0.3.7 | 3 de 3 |
| lugar de la única fila que engancha, **después** | 1 de 3 |

Las proyecciones sí se indexaban y sí se recuperaban. Lo que fallaba era el lugar: con
`max_injected` en 3 entraban raspando, y con una cuarta trayectoria en verde en el store
se caían de la inyección.

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

## Las trayectorias capturadas antes del 2026-08-26 están degradadas

Durante M1 y M2 la captura leyó tres campos del payload que no existen (spec §5.9). Lo
que quedó en el store de esas sesiones **es estructura sin contenido**: pasos sin resumen
ni error, `task_type` siempre `general`, ningún paso `contradicted`, ninguna trayectoria
cerrada como `user_corrected`.

Consecuencias que hay que tener presentes y no maquillar:

- **El conteo del gate de M1 hay que reiniciarlo, y ahora el comando lo hace solo.**
  `nightshift audit --min-sessions` cuenta **sesiones que capturaron contenido**: una
  sesión hueca no prueba ausencia de fuga, porque no se puede filtrar lo que nunca se
  guardó. Reporta las dos cifras y dice cuántas huecas descartó.
- **Las trayectorias viejas siguen ahí y no se borran.** Son inútiles para retrieval
  (todos sus pasos dicen "(sin resumen)") pero borrarlas sería reescribir el registro.
  Envejecen solas por `retrieval_lookback_days`.
- **Nada de lo que dream consolidó de ellas vale**, por el mismo motivo.

**Acción pendiente:** ninguna sobre el código. Sobre la evidencia: las 5 sesiones del gate
de M1 se cuentan **desde el fix**, no desde el principio.

---

## Deuda de proceso: `git add -A` metió los experimentos en otro commit

El commit `d6835c2` dice en su mensaje que arregla un mensaje de error, y contiene además
los tres experimentos y su documentación: 580 líneas que no menciona. Pasó por un
`git add -A` con trabajo sin commitear en el árbol.

Importa porque este repo tiene una regla explícita al respecto: *"¿Estoy describiendo lo
que construí, o lo que quería construir?"*. Un mensaje que no describe lo que el commit
contiene rompe el registro para cualquiera que lo lea después.

No se reescribió la historia: `main` es compartida. Queda anotado acá, y los experimentos
quedaron descritos en el commit siguiente.

**Acción pendiente:** ninguna sobre el código. Sobre el proceso: `git add -A` cuando hay
trabajo a medias en el árbol mete lo que encuentra, y los dos errores de proceso de esta
sesión salieron del mismo lugar — comandos que hacen algo razonable con lo que hay en vez
de fallar.

---

## Deuda de proceso: el adaptador del agente entró sin rama ni PR

El commit `5f9a446` (adaptador del agente para M4) se pusheó **directo a `main`**. La
regla de `CLAUDE.md` es una rama por milestone y PR con el gate en verde; acá hubo gate en
verde —`make check` pasó antes del commit— pero no hubo rama ni PR.

Cómo pasó, porque el modo de fallar importa más que el error: la sesión venía de mergear
el PR anterior y quedó en `main`; el comando de push tenía un fallback
`|| git push origin $(git branch --show-current)` que, al no existir la rama, empujó la
rama en la que estaba. Un fallback que "hace algo" en vez de fallar convirtió un error en
un push.

No se reescribió la historia: `main` es una rama compartida y arreglar el registro
rompiendo el registro es peor que la deuda.

**Acción pendiente:** ninguna sobre el código. Sobre el proceso: el push no debería tener
fallback, y la rama se crea antes de empezar a trabajar, no antes de pushear.

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
| Lista de reglas del redactor determinista | Se deriva de las fixtures de Histora, que no están en este repo. **Primer dato real**: sobre 86 KB capturados de una sesión de desarrollo dispararon `abs_path`, `blob`, `email`, `home_dir`, `repo_identifier`, `secret.assignment` y `secret.github`; el home no aparece en claro y `nightshift audit` sale 0. Es evidencia de que el redactor hace algo con material sucio de verdad — no reemplaza las fixtures de Histora. |
| Fixtures de Histora para los tests del redactor | Material sensible. No entran a este repo: viven fuera y el test las toma por path configurable. **El redactor tiene tests con fixtures sintéticas, no con las de Histora.** El gate de M1 no está cerrado hasta que corra contra ellas. |
| El gate de M1: 5 sesiones reales sin fuga | **El comando está** (`nightshift audit --min-sessions 5`, T1) y sobre el store real **no encuentra ninguna fuga**. Lo que falta es uso: hay 3 sesiones distintas capturadas de las 5 que pide el gate. Se cierra usando el plugin, no escribiendo código. |
| Fugas fuera del alcance de `audit` | `audit` afirma sobre lo **persistido**: rutas, secretos, home, árbol de Auto Memory, `abstraction.pattern`. No puede afirmar sobre lo que nunca se guardó ni sobre el *contenido* de un archivo negado que hubiera entrado sin su ruta. Que un `deny_path` no se capture lo defiende el redactor y sus tests, no el auditor. |
| `audit` no distingue mención de ruta más allá del separador | Un token cuenta como ruta si tiene `/`; `.env` suelto en un comentario es una mención. La regla es explicable y está testeada en los dos sentidos, pero es una heurística: una fuga escrita sin barras (`env`, `id_rsa`) no la ve. |
| Protocolo daemon ↔ hook (socket, timeouts) | Sin daemon todavía (ver arriba). Lo normativo se cumple: el hook sale 0 pase lo que pase. |
| Re-verificación del formato de hooks | Los nombres se verificaron el 2026-08-26 contra `code.claude.com/docs/en/hooks`. Cambian entre versiones: M1 re-verifica y actualiza spec §5.4 con fecha. |
| Vocabulario normalizado de tools | **Medido** sobre una sesión real de 252 pasos: `run_shell` 227, `write_file` 12, `edit_file` 5, y **`other` 1** (`AskUserQuestion`). Alcanza para una sesión de desarrollo, y el enum está congelado en el esquema de M0: no hay motivo para tocarlo. Sigue sin datos de sesiones con MCP. |
| Heurística de `task_type` | `context.TASK_TYPE_RULES` es un regex por clase, orden fijo, primera que matchea. Funciona en español e inglés y está testeada, pero es una adivinanza informada: hay que revisarla contra trayectorias reales. |
| Heurística de señal decisiva | **Medida**, y era demasiado generosa: 41% de los pasos de una sesión real marcados como concluyentes. La causa: se buscaba el comando de test como subcadena en cualquier parte, y los comandos de una sesión de trabajo son compuestos y llevan heredocs — un **título de PR** o un **mensaje de commit** que mencionaran `make check` alcanzaban. Ahora se exige posición de comando y baja a 33% sobre los mismos datos. Sigue siendo alto, y ahora es honesto: esa sesión corría tests todo el tiempo. |
| Un solo `task_type` por sesión | Una sesión larga cruza tipos de tarea —ésta cruzó implementar, analizar y depurar— y se queda con la etiqueta del primer prompt que clasifica. Partirla por tipo es rediseño, no ajuste: hay que decidir qué es "una trayectoria" cuando la sesión cambia de tema. |
| Marcas de tiempo con resolución de segundos | Ancho fijo para poder comparar en SQL, y por eso dos filas del mismo segundo empatan. Todo `ORDER BY created_at` lleva `rowid` de desempate; si alguna vez hace falta ordenar por tiempo de verdad, el formato es lo que hay que cambiar. |
| ~~`hypothesis` nunca se puebla~~ | **Hecho**: la deriva dream fase 1 de los pasos de la trayectoria, que es el único momento en que puede aparecer — la captura no persiste texto del prompt. Pasa por los mismos gates que la abstracción, y no pisa una hipótesis ya declarada. |
| ~~El resumen de un paso es lo que el agente va a leer~~ | **Hecho y verificado contra siete tools reales** (Read, Bash, Write, Edit, Glob, Grep, ToolSearch) el 2026-08-26. La sonda encontró que `Edit` devolvía `oldString` y el resumen decía que la edición había producido el texto que **borró**; ahora resume el cambio. **Falta**: las tools de MCP, que no se sondearon — para ésas sigue el fallback que busca el primer valor con texto. |

## Diferido hasta M2 (Retrieve)

| Ítem | Motivo |
|---|---|
| Dos pasadas de retrieval, dos oportunidades de gastar contexto | T2 inyecta en `SessionStart` (por repo y recencia) y otra vez en el primer prompt clasificado (por tipo). Nunca repite una trayectoria, pero una sesión puede recibir hasta `2 × max_injected`. Si eso resulta caro en contexto, el número que hay que revisar es `max_injected`, no la segunda pasada. **Sin medir.** |
| Cómo se elige `N` | Hoy `max_injected: 3` por config. El número sale de una intuición, no de medir presupuesto de contexto. |
| Los pesos del ranking | `retrieve.W_*` son constantes elegidas a mano. Son deterministas y auditables (`why` los reimprime), pero nadie las calibró. M4 es quien puede decir si sirven. |
| Ventana de las huérfanas | `orphan_after_hours: 12` es un default razonado, no medido: por debajo, una sesión inactiva pero viva (una que quedó abierta durante la noche) se cierra y la siguiente tool call abre una trayectoria nueva; por encima, una sesión muerta tarda más en volverse recuperable. Se ajusta con trayectorias reales delante. |
| Una máquina suspendida cuenta como inactividad | El barrido mira el reloj de pared, no el tiempo de CPU. Un portátil cerrado toda la noche con una sesión abierta la ve como huérfana a la mañana. Cerrarla no borra nada, pero parte la sesión si el usuario la retoma. |
| Retención y tamaño del store | Sin política. Una trayectoria por sesión y hasta 400 pasos cada una crece sin techo. `nightshift status` ya reporta el tamaño en disco (`store.store_size_bytes()`), así que la política se puede decidir con datos; la decisión en sí sigue sin tomarse. |
| Función de ranking y peso exacto de `candidate` vs `procedure` | Spec §6.3 fija el orden (candidate < procedure); el número sale de datos. |
| Cómo se usa `MEMORY.md` como señal de retrieval | Hoy sólo se detecta **si existe**, y si existe el texto inyectado lo dice. No se lee el contenido. Qué señal extraer se decide con memoria nativa real delante. |
| Transferencia cross-repo de verdad | `cross_repo` sigue **apagado** por defecto, pero el camino ya es correcto: sólo cruzan trayectorias con `abstraction` (que ahora produce dream) y de ellas se emite **sólo** el patrón, nunca los pasos. Falta la decisión de encenderlo y la evidencia de M4 de que transferir sirve. La capacidad C no está entregada. |
| ~~Plugin vs slash commands sueltos~~ | **Resuelto**: plugin. Las skills quedan namespaced como `/nightshift:<skill>`, no `/nightshift <sub>` como suponía el plan. Spec §5.5 enmendada. |

## Diferido hasta M3 (Dream + scheduler)

| Ítem | Motivo |
|---|---|
| Backend híbrido por repositorio | ADR-003 elige el backend por instalación, no por repo. Lo natural es marcar un repositorio como sensible y que ése consolide local mientras el resto usa Claude Code. No implementado: hoy es una línea de config global. |
| Migraciones del esquema del store | La primera fue `runs.cost_usd`, y funciona: agrega lo que falta y no toca lo que hay. No hay downgrade ni versionado por columna, y una migración que necesite reescribir datos —no sólo agregar— todavía no tiene forma. |
| El redactor pasó a ser también la barrera de salida | Con el backend `claude-code`, lo redactado **sale de la máquina**. Antes el redactor sólo tenía que impedir que el material sucio se persistiera; ahora es lo último antes de que salga. Sube la importancia de las fixtures de Histora, que siguen sin estar. |
| ~~El benchmark tiene dos modelos y PREREG los pide en singular~~ | **Resuelto**: `PREREG §2` los pide por separado — el del agente (interviene en las dos filas) y el de consolidación (sólo en `S1`). Los dos siguen sin fijar: son de Matías. |
| Modelo Qwen concreto y tamaño | **Sin medir.** La autodetección toma el qwen más chico ya descargado (acá `qwen3.5:4b`) porque el target es una Air de noche. Con 4b los patrones salen genéricos: sirven para el gate estructural, no está probado que sirvan para el benchmark. Qué modelo usar en M4 se decide midiendo. |
| Calidad del prompt de `consolidate` | El prompt de `dream.PROMPT` es una primera versión. Los gates que lo rodean (esquema, redactor, auditor) están testeados; que lo que produce sea *útil* no lo prueba ningún test — lo prueba M4. |
| Agrupación fina | Hoy se agrupa por tipo de tarea y nada más, porque agrupar por firma de herramientas dejaba grupos de uno. Con volumen real habrá que agrupar mejor: un `debug_test_failure` de decodificación y uno de import circular no comparten patrón, y hoy caen en el mismo grupo. |
| Una candidata por grupo y por corrida | Se promueve el representante del grupo; el resto queda `closed`. **Visto en el ensayo end-to-end:** las corridas siguientes vuelven a agarrar los que quedaron y los promueven también, así que con el tiempo casi todo termina en `candidate` y la etiqueta pierde poder de discriminar. Se corta solo por `dream_lookback_days`, no por diseño. Hay que decidir con volumen real si el criterio de promoción tiene que ser más exigente. |
| Peso de inyección de `candidate` (0.6) | Elegido a mano, como los pesos del ranking. Spec §6.3 fija el orden (`candidate` < `procedure`), no el número. |
| `dream` no puebla `hypothesis` | Sigue vacía: el modelo produce `abstraction`, no hipótesis por trayectoria. Se puede derivar, no se hizo. |
| Las tres noches del gate de M3 | El scheduler está y `schedule status` reporta las corridas. **La evidencia no está**: hay que instalar el timer en la Air y dejarlo correr tres noches. Lo hace una persona, no un agente. |
| Ventana horaria fija (03:30) | Config, pero elegida a mano. No hay medición de cuánto tarda una consolidación real ni de si entra en la ventana de batería. |
| `schedule status` no dice cuándo es la próxima corrida en `systemd` ni en `loop` | Se resolvió para `launchd`: `LaunchdBackend.next_run()` calcula la próxima corrida desde el `Hour`/`Minute` del propio plist, sin parsear `launchctl print` (formato no versionado). Falta el mismo cálculo para `systemd` (`OnCalendar`) y una noción equivalente para `loop` (próximo vencimiento del intervalo). |
| El backend `loop` no sobrevive a un reinicio | Es el backend de desarrollo, corre en primer plano y muere con la terminal. Documentado, no arreglado: para eso están los otros dos. |
| Política de retención del store | No hay volumen real todavía. Decidir con datos, no con intuición. |

## Diferido hasta M4 (Benchmark)

| Ítem | Motivo |
|---|---|
| Todos los `TODO(Matias)` de `bench/PREREG.md` | **Claude Code no fija umbrales** (plan §5). Los resuelve una persona antes de congelar. El runner ya los lee: `nightshift bench check` lista los 22 con su sección y su línea. |
| ~~Cómo se lanza el agente en cada celda~~ | **Construido**: `bench/agentes/correr-agente.py` arma la invocación de las filas S0 y S1, cuenta las tool calls del stream y se niega a correr sin las constantes pre-registradas. Lo que sigue siendo de Matías son esas constantes. |
| El límite de tool calls no se puede imponer | Verificado el 2026-08-26: el CLI de Claude Code no expone `--max-turns`. El adaptador **mide** las tool calls y reporta `tool_limit_exceeded`; imponer el límite necesita una feature del harness que hoy no existe. Un límite que se declara y no se aplica hay que decirlo. |
| (histórico) Cómo se lanza el agente en cada celda | El runner recibe el comando por `--agent`. Cuál es ese comando para S0 y para S1 —con nightshift apagado y encendido, con Auto Memory en el mismo estado— es parte del protocolo, y el protocolo de reset entre corridas es un `TODO(Matias)` de PREREG §5. |
| Conteo de tool calls | Métrica secundaria de A y C. El runner registra lo que el agente imprima; si no imprime nada queda en `null` y el reporte lo dice. Contarlas es cosa del harness: estimarlas sería inventar un dato. **El adaptador las cuenta de los bloques `tool_use` del stream**, y el runner guarda además `num_turns`, `cost_usd` y `tool_limit_exceeded`. |
| La mitad "cero regresión" de la regla de decisión | La tolerancia es un `TODO(Matias)`. El runner evalúa la mitad que puede (≥2 de 3 familias) y **dice explícitamente** que la otra mitad no se evaluó. |
| Fixtures reales de A, C y D | Los sintéticos de `bench/fixtures/selftest/` prueban el runner, no nightshift. Los de verdad —dos repos, 10 bugs con causa compartida, ground truth de contradicciones— los define Matías con PREREG. |
| ~~Repos fixture de las familias A y C~~ | **Construidos** en `bench/fixtures/familia-{a,c,d}/`, con `nightshift bench fixtures` afirmando que cada tarea falla antes y la resuelve su fix de referencia. Falta que Matías **congele sus identificadores** en PREREG: eso sigue siendo `TODO(Matias)`. |
| Cómo se enumeran las memorias inyectadas en la fila S0 (familia D) | El clasificador de la familia D sólo puede medir S1: en S0 nightshift no está, y las memorias de Auto Memory no son visibles — no hay API, y leerlas sería tocar el árbol nativo, que ADR-001 prohíbe. **Sin esto, la familia D es indecidible**, y el runner lo reporta así en vez de inventar un baseline. Es `TODO(Matias)`. |
| Contaminación de los fixtures | Los repos fixture son código nuevo escrito para esto, no proyectos existentes: eso reduce la chance de que estén en los datos de entrenamiento, pero no la elimina ni la mide. La mitigación de PREREG §5 sigue siendo `TODO(Matias)`. |
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

## Seis amenazas a la validez que no estaban en PREREG §5

Ninguna rompía nada: las seis producían un número confiado y falso, y las seis
aparecieron mirando el sistema andar.

| Amenaza | Qué habría medido | Cómo apareció |
|---|---|---|
| Store de nightshift por celda | La fase de aprendizaje no le enseñaba nada a la de medición: **cero transferencia por construcción**, o sea un no-go garantizado sin importar si nightshift sirve. | corriendo el chain |
| Ruta de trabajo nueva por tarea | Auto Memory keyea por ruta de proyecto y nightshift por fingerprint del repo. Arreglar sólo el lado de nightshift habría dado ventaja a nightshift **por construcción**: el error opuesto y peor, porque favorece a lo que se mide. | corriendo el chain |
| **La familia C no cruzaba de repositorio** | Sus dos "repos" vivían bajo un solo `git init` en la raíz del directorio de trabajo, y el agente corría ahí: para nightshift eran **el mismo repo**, con el mismo fingerprint. La familia de la capacidad C no ejercitaba la capacidad C. Ahora son dos repos git con remotes distintos y cada tarea corre dentro del suyo. | el segundo ensayo sellado |
| **La segunda tarea de medición de la familia C no mide cross-repo** | Las dos tareas de medición viven en el repo B y comparten store dentro de una repetición, así que la segunda recibe la memoria de la primera: eso es transferencia *dentro* de B, no de A a B. Medido: 1 de 2 celdas de medición recibió memoria. Cuántas tareas de medición por repetición, y si la acumulación dentro de B es aceptable, es una constante del experimento que **no está en PREREG**. |
| **La historia de la familia D se sembraba con un fingerprint inventado** | El retrieval la descartaba por ser "de otro repo": la familia habría medido precisión sobre cero memorias inyectadas. | el primer ensayo sellado |
| **`cross_repo` apagado en la familia C** | La familia C mide transferencia entre repos, y con `cross_repo: false` —el default— la fila S1 recibe **cero memorias** en el repo B. La familia daría cero transferencia gane o pierda nightshift. Medido: 0 candidatas con el default, 1 con el flag encendido. | auditando el plan original |

**Acción pendiente antes de congelar:** el valor de `cross_repo` para la fila S1 es una
constante del experimento y no está en `PREREG §2`. Encenderlo tampoco es gratis: hoy la
capacidad C está declarada *no entregada* justamente porque cruzar de repo sin abstracción
transfiere detalle. Con dream produciendo abstracciones eso cambió, pero la decisión es de
Matías y va escrita antes de correr.

Y una lectura que ya no es anécdota: la lista de amenazas de §5 se demostró incompleta
**seis veces**, y las tres aparecieron mirando el sistema andar, no leyendo el documento.

Las dos se arreglaron con la misma decisión: un directorio de trabajo y un store por
**(fila, repetición)**, con el contenido del repo reseteado antes de cada tarea. Queda
como recordatorio de que las amenazas a la validez de PREREG §5 no son todas las que hay:
ésas dos no estaban en la lista y aparecieron a los cinco minutos de correr la cosa.

---

## Sobre el ensayo end-to-end

`nightshift simulate` corre la máquina entera con sesiones sintéticas y tres noches
simuladas, y **no cierra ningún gate**. Está acá para que quede escrito por qué:

| Gate | Qué pide | Por qué el ensayo no alcanza |
|---|---|---|
| M1 | 5 sesiones **reales** sin fuga | Las sesiones sintéticas las escribe nightshift: probar el redactor contra material que uno mismo eligió no es lo mismo que contra una sesión de trabajo real. Y el ensayo corre en un store desechable a propósito — el conteo del gate no se puede inflar. |
| M3 | 3 **noches** seguidas sin intervención | Tres corridas en un bucle no tienen suspensión, ni batería, ni un `launchd` que se olvidó de disparar. El gate mide el sistema operativo tanto como el código. |

Lo que el ensayo sí sirve: encontrar que la máquina se rompió, hoy, sin esperar semanas.
Encontró dos cosas reales — los códigos de salida de la corrida nocturna y el crecimiento
de `candidate` de arriba.

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
6. **Si la configuración de retrieval entra al pre-registro.** PREREG §2 fija el modelo
   del agente, el de consolidación y la `consolidation_strategy` porque cambian qué
   **es** el brazo S1. La configuración de retrieval —`max_injected`, `cross_repo` y la
   función de ranking de `retrieve.W_*`— decide qué se inyecta, que es literalmente el
   tratamiento, y **no** está pre-registrada. El 2026-08-27 el ranking cambió (enganche
   por fallo observado, spec §5.10) y nada en el pre-registro habría dejado constancia de
   que el brazo cambió. Anotarlo en PREREG es de Matías: la regla 3 del pre-registro dice
   que Claude Code lee y no propone, así que el agujero se deja escrito acá y no allá.
7. **Las ocho preguntas de [`PLAN-M4.md` §10](doc/PLAN-M4.md).** Salieron de reordenar el
   plan el 2026-08-27. Ninguna la puede cerrar un agente: o son decisiones, o cambian qué
   mide el experimento. Descartar una es una respuesta.

## Los dólares del benchmark no eran una factura

`claude -p --output-format json` devuelve `total_cost_usd`, y yo lo reporté como
"costo" — de ahí salió el "USD 22 las 102 celdas" del ensayo. El campo viene con
`costBasis: "list"`: es la valorización **a precio de lista** de ese uso, no lo que se
paga. Con la suscripción de Claude Code no se factura nada de eso.

Sirve como vara para comparar una corrida con otra, así que no se tira: se etiqueta. Lo
que sí se consume es **tokens**, y ahora son la cifra que va primero — en el ensayo, en
el reporte del benchmark, en `dream` y en `why`. Un test recorre la salida del ensayo y
falla si alguna línea con `USD` no dice "a precio de lista".

Queda anotado para PREREG: el presupuesto de M4 se expresa en tokens o en tiempo de
pared, no en dólares. Cuál de los dos, y con qué tope, es `TODO(Matias)` — no lo decido
yo, pero el número que estaba escrito era engañoso y ya no está.


## El orden de la matriz era una trampa esperando un corte

La matriz iba **fila → repetición**: todas las repeticiones de S0 y después todas las de
S1. Mientras la corrida terminara entera daba igual. Con un presupuesto de tiempo deja de
dar igual: cortar por falta de ventana dejaba S0 completa y S1 a la mitad, y eso no es un
experimento más chico sino uno torcido — dos brazos con distinto n presentados como una
comparación.

Ahora va **repetición → fila**. Cortar al terminar una repetición deja las dos filas con
exactamente las mismas. Las celdas son independientes (directorio de trabajo y store
propios por fila y repetición), así que el reorden no cambia nada de lo que se mide.

Nadie lo habría notado hasta la primera corrida cortada, que es justo la que uno mira con
menos ganas de dudar.

## `ideate`: idear en imágenes antes de abstraer

Idea de Matías. Antes de razonar —o antes del bloque de thinking— **idear**: describir el
mecanismo como lo hace una persona, en imágenes. Un diagrama, una escena, dos cuadros de
animación. Cómo un algoritmo recorre el área bajo una curva, cómo un banco de filtros
deforma una señal, cómo se ven los bloques de un LLM interactuando, cómo va a quedar una
obra, qué hace la física en una escena.

La parte que se puede probar hoy, y que probé: **el dibujo de un mecanismo es invariante
entre síntomas de un modo que la prosa no lo es.** Si vale, una abstracción hecha desde el
dibujo transfiere a un síntoma que nunca vio — que es justo lo que le faltó al
experimento 01.

Está corrido y documentado en `experimentos/04-ideacion-visual.sh`. Resumen: con el mismo
corpus, el patrón ideado describe la **forma** («una capa que tapa a otra») donde el
control describe el **caso** (nombra `unittest`, `git stash`). En la prueba ciega el
ideado le ganó al control, 16 turns contra 26 — y los dos perdieron contra no tener
memoria, 13. Con un brazo por celda eso no distingue nada: la varianza entre corridas
idénticas ya medida es más grande que la diferencia.

**No entra al plugin.** El bloque vive en `experimentos/`, y si resulta que sirve entra
por el camino normal. Meterlo en `dream.py` ahora sería cambiar el consolidador justo
antes de M4, con evidencia de n=1 — exactamente lo que el pre-registro existe para
impedir.

**Lo que falta para decidirlo:** el diseño de M4 aplicado a esto — varios síntomas ciegos,
tres corridas por brazo, umbral antes. Es una familia más, no un ajuste de prompt.

### La parte grande, que es otro proyecto

Lo que sigue de la idea —mapear el dibujo a **oráculos de dominios distintos** (un
simulador de física, un CAS, un renderer, un motor de señales) y a una base de conocimiento
externa, para inferir vías de resolución que no están en los pesos— no es un ajuste a
nightshift. Es otra tesis: nightshift dice que **cómo se averiguó algo** transfiere; ésta
dice que **la forma del mecanismo** transfiere entre dominios, y que un oráculo externo
puede validarla sin que el modelo la sepa.

Sería la primera cosa del proyecto que necesita algo más que `subprocess` y stdlib, así
que también choca con ADR-003. No la abro acá. Queda escrita porque es buena y porque
dentro de seis meses nadie se va a acordar de por qué no se hizo.

## El plugin, soñando sobre su propio desarrollo, encontró que un día no es una trayectoria

Matías pidió usar el plugin sobre sí mismo: cerrar el capítulo de esta sesión y forzar
ciclos de sueño sobre el desarrollo del propio plugin. Corrido con `ideate` (ADR-004),
sobre el store real.

**Lo que consolidó** fue el bug de los campos del payload, y lo dibujó así:

> «una cadena de transporte donde cada eslabón conserva el sobre y descarta la carta… una
> junta que gotea hacia adentro, un tubo que sigue teniendo presión aguas abajo aunque ya
> no lleve fluido.»

Y proyectó cuatro síntomas. Una se puede comprobar contra el código hoy, y la comprobé:

- *«los contadores de cobertura reportan salud plena porque cuentan registros presentes,
  no registros con contenido»* — **no se sostiene**: `with_outcome` cuenta veredictos
  reales del gate y `capture_quality` mide el vacío explícitamente. Es el bug que ya se
  arregló en el gate de M1, y no quedó otro igual.

Una conjetura comprobada y descartada. Eso es lo que la distingue de un dato, y es
exactamente el trabajo que `verify` (M5) va a tener que hacer solo.

### Corrección del 2026-08-27 (tarde): acá había una segunda refutación que no existe

**Este párrafo decía dos, y la segunda no es trazable.** Afirmaba haber refutado también
*«un gate que pasa en verde habiendo ejecutado cero tests»*, atribuyéndola a las mismas
cuatro proyecciones de esta consolidación. Buscada de nuevo: **esa frase no está en el
store, ni en los logs, ni en ninguna salida guardada de dream.** Las cuatro proyecciones
de la candidata `fff6af83` son, textuales:

1. «El retrieval devuelve coincidencias por forma estructural sin relación con el
   contenido del trabajo.» — **confirmada** (spec §5.10)
2. «Las memorias consolidadas de trabajos distintos resultan casi idénticas entre sí.» —
   **abierta**
3. «Los contadores de cobertura reportan salud plena porque cuentan registros presentes,
   no registros con contenido.» — **refutada**, arriba
4. «Una revisión manual de un registro reciente muestra la estructura completa y todos los
   campos de texto en blanco.» — **confirmada** (spec §6.1)

Lo más probable es que sea una paráfrasis de memoria de la proyección del experimento de
ideación —*«un test recién agregado no se ejecuta nunca y nadie lo advierte, porque el
total no se compara contra ningún valor esperado»*— que ADR-004 **confirmó** y que produjo
`tests/test_suite.py`. Si es así, el párrafo original le dio vuelta el veredicto a la única
proyección que este proyecto puede mostrar habiendo cerrado un agujero real.

**Y eso es exactamente lo que este archivo dice tres secciones más arriba:** "una
explicación plausible anotada como hallazgo es exactamente el tipo de memoria que este
proyecto dice no querer". Costó otra vez, en la misma página, y esta vez sobre el único
número que el proyecto publica. Queda escrita la corrección y no se borra el error.

**Y lo que NO consolidó es el hallazgo.** La trayectoria de esta sesión —400 pasos, un
día entero de desarrollo— salió como *«sin patrón común»* en los dos ciclos. No es un
fallo del modelo: dream agrupa por tipo de tarea, así que un día entero de trabajo
heterogéneo es **un grupo de uno**, y de una sola trayectoria no hay nada compartido que
abstraer.

**nightshift no tiene noción de capítulo.** La sesión es la unidad de captura y la
trayectoria es la unidad de consolidación, así que las dos son lo mismo — y cuanto más
productivo es el día, menos consolidable queda. Un día con quince tandas de trabajo, cada
una con su rama, su gate y su merge, se guarda como una cosa sola que no se parece a nada.

Lo que haría falta —segmentar una sesión larga en capítulos, probablemente por el
desenlace: cada `make check` en verde y cada merge cierra uno— es una capacidad que no
está en el plan v0.3 y que no abro acá. Queda escrito con el dato que lo motivó: **dos
ciclos de sueño sobre 400 pasos de desarrollo real produjeron cero candidatas.**

### Corrección del 2026-08-27: el diagnóstico de arriba era el equivocado

Lo anterior queda como estaba porque es lo que se creyó y sobre eso se decidió. **No era
la causa.** Se aisló la variable corriendo el modelo de verdad sobre stores desechables:

| Experimento | Resultado |
|---|---|
| Grupo de **una** trayectoria con contenido (`cbbd7ff0`) | **candidata** |
| Grupo de dos (`8347ad4f` + `cbbd7ff0`) | **candidata** + una contradicción enlazada |
| Grupo de una silueta (`a49c1582`, todos los pasos vacíos) | sin patrón común |
| Grupo de **una**: los 400 pasos, 177 con contenido | **sin patrón común** ← el caso a explicar |

Un grupo de uno **sí** produce candidata: la hipótesis de que hacía falta compartir
patrón entre trayectorias era falsa, y el prompt —que pide "el patrón que comparten"— no
era lo que bloqueaba. Lo que bloqueaba era **qué pasos veía el modelo**: seis por
trayectoria, elegidos por la bandera `decisive`, sin exigirles contenido. Para esa
trayectoria los seis salieron vacíos mientras 177 pasos con texto no se miraban.

Arreglado (spec §6.1, enmienda 0.3.5): al prompt van los pasos con contenido, fallos
primero. La misma trayectoria, el mismo store, el mismo costo (~38 k tokens de entrada):
antes `sin patrón común`, después una candidata sobre el problema real de esa sesión.

**Lo del capítulo sigue en pie, pero como problema de calidad, no de cantidad.** Un día
entero sigue siendo una trayectoria sola, y de un día heterogéneo sale una candidata que
lo promedia. Que ahora salga *algo* no vuelve buena la unidad de consolidación.

Y queda una lección sobre este mismo archivo: **una explicación plausible anotada como
hallazgo es exactamente el tipo de memoria que este proyecto dice no querer.** El párrafo
de arriba se escribió sin aislar la variable, y sonaba lo bastante bien como para que
nadie lo revisara durante un día.

## La ideación se fue a 4.866 tokens de salida por grupo

Pedirle la visualización canónica —la DFT como centro de masa, la convolución como
solapamiento— mejoró mucho el dibujo y casi **triplicó la salida**: 1.715 tokens antes,
4.866 después, por grupo. El texto se inyecta recortado (`MAX_IDEACION_CHARS`), así que el
costo es de consolidación, no de contexto.

Con `dream_max_groups` sin tope, una noche con muchos grupos lo multiplica. No toco el
default: el tope por corrida ya existe y cuánto vale una noche de dream es una decisión de
Matías, no mía. Queda el número medido para que la decisión se tome con él.

También: el bloque decía «es un boceto, no un tratado» y el modelo devolvía ~2.600
caracteres igual. La instrucción de brevedad no funcionaba. **Resuelto en ADR-005**: el
dibujo se pide como diagrama Mermaid con tope de nodos, y la magnitud perdida como un
campo aparte. Un diagrama tiene un límite natural que la prosa no tiene.

## `decisive` marca el 38% de los pasos, y eso no es una señal decisiva

> **Cerrado el 2026-08-27** (spec §4.3 y §4.3.1). Se eligió apretar la bandera, no
> partirla: `decisive` la enciende un fallo, y `tests_passed` se infiere del comando
> guardado. Partirla en `decisive` + `outcome_signal` pedía `trajectory.v2` y una
> migración, y el desenlace se calcula igual de bien sin bandera. Queda el texto porque
> el número que lo motivó es lo que permite saber después si el arreglo sirvió.

Medido sobre el store real (471 pasos, 2026-08-27), no estimado:

| | |
|---|---|
| pasos decisivos | 180 de 471 — **38%** |
| de los 159 de una sola trayectoria | **151 son `tool_use`**: comandos de test que pasaron |
| fallos de verdad (`tool_failure` con texto) | **4 en todo el store** |

La spec §4.3 define `decisive` como "el paso donde la señal se volvió concluyente". La
heurística implementada marca dos cosas distintas con la misma bandera: un fallo
observado —que es diagnóstico— y cualquier comando de test que corrió —que es evidencia
de **desenlace**. Mezcladas, ninguna de las dos discrimina.

Dónde se paga hoy:

- **En el ranking.** `W_DECISIVE` se cobra por tener *algún* paso decisivo, y como casi
  toda trayectoria corre tests alguna vez, se cobra casi siempre: un peso que puntúa a
  todos no ordena a nadie.
- **En el desenlace.** `hook._infer_outcome` devuelve `tests_passed` si hay un paso
  decisivo `tool_use` de shell. Un comando de test **que pasa** es un `tool_use`, sí; lo
  que no se comprueba es que ése sea el último estado, ni cuál test.
- **En dream.** Es lo que el prompt de consolidación le señala al modelo como "acá está
  la señal". Si el 38% de los pasos es señal, no hay señal.

El enganche por síntoma (spec §5.10) esquiva el problema mirando sólo `tool_failure`, que
es la mitad no contaminada. Arreglar la bandera en sí es otra cosa: toca captura y
desenlace a la vez, y hay que decidir si se parte en dos banderas (`decisive` diagnóstica
y `outcome_signal`) o si se aprieta la heurística. **No lo abro acá**: cambia el
significado de un campo del esquema y de una métrica que ya se reporta.

## `valid_when` se muestra y no se busca

> **Cerrado el 2026-08-27** (spec §5.10). Engancha con motivo propio, `precondition_match`,
> en commit separado del enganche por fallo para que M4 pueda atribuir cuál movió el
> ranking. Pesa 1.0: observado > inferido > conjeturado.

Las precondiciones son la mitad del valor de una alternativa descartada —"la descartada
seguía teniendo razón cuando el límite era realmente bajo"— y hoy son **sólo de salida**:
`render()` las imprime, `candidates()` nunca las mira. Una trayectoria cuyas
precondiciones describen exactamente la situación que el usuario tiene delante no puntúa
por eso ni un punto.

No lo hago junto con el enganche por fallo: son dos claves de recuperación distintas
—una es "esto ya lo vi", la otra es "esto aplica acá"— y meterlas en el mismo commit hace
imposible saber cuál de las dos movió el ranking cuando M4 lo mida.

## La calidad de la captura promedia un bug ya arreglado

> **Cerrado el 2026-08-27.** Las trayectorias declaran `capture_cohort` y `status` sólo
> promedia la actual; las anteriores se cuentan y se nombran. Lo que **sigue abierto** es
> lo del final: `Edit` y `Write` no los usó ninguna sesión posterior al arreglo, así que
> su captura sigue sin verse funcionar.

`status` reporta **52% de pasos de tool sin contenido** y `doctor` mira la última
trayectoria. Los dos números son ciertos y dicen cosas opuestas, porque el 52% es un
promedio sobre las últimas cuatro trayectorias y dos de ellas son cascarón del bug de los
campos del payload (2026-08-26). Desglosado:

| trayectoria | pasos de tool | sin contenido |
|---|---|---|
| `8347ad4f` (pre-arreglo) | 384 | 223 (58%) |
| `a49c1582` (pre-arreglo) | 7 | 7 (100%) |
| `cbbd7ff0` (post-arreglo) | 52 | **1 (2%)** |

La captura de hoy trae contenido en el 98% de los pasos. El alarma que HANDOFF le manda
mirar primero a la sesión siguiente es, en su mayor parte, historia — y ése es el riesgo:
una métrica que suena la alarma para siempre es una métrica en la que una regresión nueva
se esconde dentro del promedio. Lo que falta es que la ventana distinga cohortes —o que
el número sea por trayectoria y no un promedio— y esa decisión necesita mirar si vale la
pena marcar las trayectorias degradadas en el store o dejarlas envejecer solas.

Lo que **no** está medido después del arreglo: `Edit` y `Write`. Las dos aparecen vacías
en las trayectorias viejas, ninguna sesión posterior al arreglo las usó (`cbbd7ff0` es
todo `Bash`), y el sondeo de §5.9 dice que sus formas se leyeron bien. Nadie lo vio
funcionar todavía.

## La relación entre enganchar por síntoma y coincidir de tipo no está calibrada

`W_FAILURE_MATCH` vale 1.5, lo mismo que `W_SIGNAL_MATCH`, y `W_SAME_TASK` vale 2.0. Es
decir: hoy una coincidencia de **categoría** (hay seis tipos de tarea) pesa más que haber
visto **ese mismo fallo**. Puede estar bien —el tipo de tarea es la clave estructural de
la spec— o puede ser exactamente al revés. Es otro de los pesos elegidos a mano que M4 va
a poder juzgar; queda anotado junto a los demás en "Diferido hasta M2".

## Idea de Matías: presentar lo soñado como opciones, y decidirlo con el usuario

Del 2026-08-27, mirando cómo esta misma sesión resolvió sus bloqueos: cuando un agente no
puede decidir algo, presenta **opciones concretas con su consecuencia** y sigue con la
respuesta. La observación es que ésa es exactamente la forma que le falta a lo que dream
produce:

> «el mecanismo con el que a veces preguntás sobre un plan, en el que das varias opciones
> y de acuerdo a las respuestas reorientás el plan, es justamente como deberíamos
> presentar las trayectorias futuras generadas por sueño y validarlas con el usuario o
> resolver sus gaps con human in the loop»
>
> «es casi como que en sueño simulás esas opciones, y contrastás los agentes que están
> siguiendo diferentes paths entre ellos para que pulan y refinen sus propuestas a futuro»

Encaja con dos cosas que ya existen y que hoy no llegan a ningún lado:

- **`projected_signals`** (ADR-004) son conjeturas que nadie observó. Se inyectan con la
  mitad del peso y anunciadas como tales, y **nada las resuelve nunca**: no hay forma de
  que una conjetura pase a ser otra cosa. Una validación humana es una.
- **El contraste** (ADR-005) hoy compara **dos trayectorias que existieron**. Lo que
  propone la idea es contrastar **caminos que no se recorrieron**: varios agentes
  siguiendo alternativas distintas, puliendo la propuesta unos contra otros antes de que
  la vea nadie.

**La distinción que hay que defender si esto se construye:** un humano validando una
conjetura **no es `verify`**. ADR-002 define verificar como reproducir contra un gate —un
comando, un exit code, un `run_id`— y "el usuario dijo que sí" no es eso. Sería un tercer
estado, algo como `human_reviewed`, con su propio peso: más que una conjetura, menos que
una reproducción. Colarlo como `procedure` sería exactamente el tipo de fabricación de
evidencia que el proyecto tiene prohibida.

Lo que aporta y lo que arriesga, sin adornos:

| | |
|---|---|
| Aporta | La única forma barata de resolver el gap de una proyección hoy. Y las respuestas del humano son señal de entrenamiento para el ranking: qué proyección era útil y cuál era ruido |
| Arriesga | Preguntar es caro para el usuario. Un dream que consolida en silencio no interrumpe; uno que pregunta, sí. El presupuesto de preguntas por noche es una decisión, no un default |
| Arriesga | Contrastar agentes multiplica el costo de consolidación por el número de caminos, y ADR-003 ya hizo que consolidar cueste |

**No entra al plugin, y sí hay prototipo.** Decidido con Matías el 2026-08-27:
`experimentos/preguntar.py` prueba la mitad barata —la forma de la pregunta— sin tocar el
flujo por defecto, sin participar del brazo S1 y sin escribir en el store (lo abre en modo
sólo lectura de SQLite). La otra mitad —contrastar agentes que siguen caminos distintos—
cuesta una consolidación por camino y queda para después del veredicto: si M4 dice no-go
no se construye, y si dice go compite con M5 (`verify`) por ser lo siguiente.

**Lo primero que mostró el prototipo, y es incómodo:** de las cuatro proyecciones que dream
escribió el 2026-08-27 sobre el store de este repo —en la corrida de las **15:25:34Z**, que
es la que produjo la candidata; la de las 15:27 produjo cero—, **dos se confirmaron esa
misma tarde**: el retrieval que coincidía por forma sin mirar contenido, y el registro con
la estructura completa y los campos de texto en blanco. Ninguna de las dos se encontró
*por* la proyección: estaban escritas, inyectadas y disponibles, y el trabajo las
redescubrió midiendo por otro motivo. Una conjetura que nadie resuelve no es memoria, es
una nota.

El puntaje completo y trazable es **cuatro proyecciones: 2 confirmadas, 1 refutada, 1
abierta**, de una sola candidata en un solo store. Antes acá decía "2 y 2 sobre seis", y
las dos cuentas de más no existen — la corrección está más arriba, en la sección de esta
misma consolidación.

## El enganche por síntoma no sabe de sinónimos

Encontrado el 2026-08-27 midiendo lo que nadie había medido: la spec §5.10 verificó que el
ranking **discrimina** —dos prompts distintos, órdenes distintos— pero nunca que
**sobreviva a la paráfrasis**, que es la única forma en que una persona escribe. Se caía a
1 de 6 sobre el store real. La enmienda 0.3.6 lo llevó a 4 de 6 y el detalle está en
`experimentos/05-enganche-por-parafrasis.py`.

**Las otras dos no se arreglan bajando un piso.** Son estas:

- «dos resúmenes de tareas diferentes me salieron prácticamente iguales», que tendría que
  enganchar con «las memorias consolidadas de trabajos distintos resultan casi idénticas
  entre sí».
- «las métricas dicen que está todo bien pero es mentira», contra «los contadores de
  cobertura reportan salud plena porque cuentan registros presentes».

No comparten **ninguna** palabra de contenido con la frase que las describe. `resumen` y
`memoria consolidada`, `métrica` y `contador de cobertura`, `mentira` y `salud plena` son
el mismo concepto con vocabulario distinto, y la intersección de tokens no tiene forma de
saberlo. Se probaron dos sustitutos de stdlib y **ninguno compra nada**, con su número en
el experimento:

| matcher | paráfrasis | falsos |
|---|---|---|
| antes: piso único 2 | 3/14 | 0/6 |
| ahora: destilado piso 1 | 9/14 | 0/6 |
| prefijo de 5 caracteres | 3/14 | 0/6 |
| `difflib` a 0.82 | 3/14 | 0/6 |

Los dos últimos atacan morfología —plurales, tipeos— y el problema es semántico. Lo que lo
resolvería son embeddings, y ahí choca con dos cosas a la vez: **ADR-003** (sólo stdlib,
sin red, nada que pida una API key nueva) y el hecho de que un índice vectorial local es la
primera pieza del proyecto que necesitaría un modelo corriendo en el camino caliente de un
hook, que tiene que salir en milisegundos y salir 0 siempre.

**No lo abro**, y no por costo sino por orden: es una mejora del brazo `S1` y M4 todavía no
dijo si el brazo `S1` vale la pena. Si M4 da no-go, esto no se construye. Si da go, compite
con M5 (`verify`) por ser lo siguiente — y `verify` gana, porque hoy nada llega a
`procedure` y eso es un agujero más grande que un enganche que falla en 2 de 6.

Queda escrito con el número que lo motiva, que es lo que le faltaba a la versión anterior
de esta página.
