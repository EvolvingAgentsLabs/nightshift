# HANDOFF — control del desarrollo

Documento para la sesión de Claude Code que continúa el desarrollo de nightshift.
Se lee entero antes de tocar nada.

---

## 0-bis. El pivot del 2026-08-27 — las tres ideas

**Decidido por Matías.** Esta sección manda sobre el camino crítico de
[`PLAN-M4.md`](PLAN-M4.md), que queda pausado entero.

El proyecto no se destrabó porque alguien tomara las decisiones que lo bloqueaban: se
destrabó porque esas decisiones **salieron del camino crítico**. Lo que queda es un solo
objetivo y una sola forma de saber si funciona.

### El objetivo, y son tres ideas

1. **CTE — Chain of Thought is Chain of Execution.** Una trayectoria no es el registro de
   lo que un agente pensó: es lo que ejecutó. Lo que nightshift captura ya es la cadena, y
   por eso vale la pena consolidarla — no hay que reconstruir el razonamiento desde
   afuera, está en los pasos.
2. **Correr la cadena para adelante, no para atrás.** Consolidar mirando hacia atrás
   produce memoria de lo que ya pasó, que sólo sirve cuando el síntoma se repite idéntico.
   Lo que hace falta es **proyectar**: desde el mecanismo, anticipar en qué otras formas
   se va a manifestar, y que esas conjeturas lleguen al agente **antes** de que el error
   ocurra.
3. **Idear en vez de razonar.** Antes de abstraer, dibujar: el mecanismo como diagrama.
   La hipótesis es que el dibujo de un mecanismo es invariante entre síntomas de un modo
   que la prosa no lo es (ADR-004). Es de ahí que salen las proyecciones de la idea 2.

Las tres se implementan en un solo lugar: `dream.consolidate`, que ahora idea siempre, y
`retrieve.candidates`, que ahora pone lo que engancha con el prompt delante de lo que sólo
comparte repo o tipo de tarea.

### Lo que queda pausado, y qué no cambia por pausarlo

| Qué | Estado | Qué **no** cambia |
|---|---|---|
| **M4 — benchmark go/no-go** | **PAUSADO.** Fuera del camino crítico | El runner sigue construido y sigue **negándose a correr**. `bench/PREREG.md` conserva sus `TODO(Matias)` **sin tocar**: pausar el benchmark no es completar el pre-registro, y completarlo sigue siendo una violación |
| **Gate humano de M0** — revisión de ADR-001 por Ismael | **PAUSADO.** Deja de bloquear | Sigue pendiente y sigue siendo cierto que hay código construido sobre las cinco capacidades que ese ADR decide. No lo des por cerrado: darlo por cerrado es distinto de no esperarlo |
| **Gate de M1** (5 sesiones) y **gate de M3** (3 noches) | Dejan de bloquear | Siguen siendo evidencia real cuando ocurran. `nightshift audit --min-sessions 5` y `nightshift schedule status` siguen diciendo la verdad, y la verdad hoy es que ninguno de los dos está cerrado |
| **M5 — dream fase 2 (`verify`)** | **SIGUE PROHIBIDO** | Y el motivo cambió: antes esperaba el veredicto de M4, que ya no va a llegar. Ahora lo que lo prohíbe es que nada llega a `procedure` y el dogfooding **no** lo desbloquea. Verificar es lo más caro de construir y nadie midió todavía que valga la pena |
| **Adapter de OpenCode** | Prohibido, sin cambio | — |

Lo que **no** se pausa, porque no es burocracia: las prohibiciones de `CLAUDE.md`. Stdlib
pura, sin red, sin escribir en el árbol de Auto Memory, hooks que salen 0, y no presentar
nightshift como reemplazo de Auto Memory. Un pivot de objetivo no es un permiso.

### El gate nuevo: dogfooding

**El agente usando nightshift sobre el código de nightshift.** Y como un gate es un script
y no un juicio (`CLAUDE.md` regla 2), es esto:

```sh
make dogfood
```

Corre `make check` y después, **sobre el store real y no sobre uno desechable**:
`doctor`, `audit` y `status`. Pasa si el gate está en verde, la captura de la última
sesión trae contenido, el store no tiene fugas y hay trayectorias de este repo.

**Lo que este gate no dice, y conviene decirlo antes de que alguien lo cite mal:**

- No dice que la memoria **sirva**. Eso era lo que M4 iba a medir, y no se midió. Lo que
  dice es que la máquina corre sobre su propio material sin romperse ni filtrar nada.
- No convierte una `candidate` en `procedure`. Nada está verificado, y la inyección lo
  sigue diciendo en cada corrida.
- Un ensayo (`make simulate`) sigue sin cerrarlo: `dogfood` mira el store real a propósito.

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
| Auditoría del store (gate de M1) | `nightshift/audit.py` |
| Dream fase 1 — `consolidate`, con ideación y proyección | `nightshift/dream.py` |
| Contraste entre una alternativa descartada y la que la reemplazó | `nightshift/dream.py`, `store.mark_superseded` |
| Scheduler pluggable + registro de corridas | `nightshift/schedule.py` |
| Cohorte de captura: `status` no promedia entre generaciones | `store.COHORTE_DE_CAPTURA` |
| Runner del benchmark de M4 (se niega a correr) | `nightshift/bench.py` |
| CLI y skills | `nightshift/cli.py`, `skills/` |
| Gate | `make check` — lint-docs, lint-code, schema, 305 tests, selftest |
| Gate del pivot | `make dogfood` — `check` y después `doctor`, `audit` y `status` sobre el store **real** |
| Gate con modelo local | `make dream-selftest` — fuera de `check` a propósito |

### No construido

Dream fase 2 (`verify`). El benchmark tiene runner pero **no tiene resultados**: no
corrió nunca y no puede correr hasta que el pre-registro esté congelado. Hay
`candidate`, pero **nada llega a `procedure`**: ninguna memoria inyectada está verificada.
Una `candidate` la abstrajo un modelo y nadie la reprodujo contra un gate. No lo describas como si lo estuviera,
ni en el README, ni en un commit, ni en una demo.

### Pausado — ya no bloquea, y tampoco se dio por hecho

**Ver §0-bis, que es donde se decidió.** Resumen, porque la diferencia entre "pausado" y
"cerrado" es exactamente donde este repo ya se equivocó una vez:

- **M4 (benchmark go/no-go)** — pausado. Lee umbrales de `bench/PREREG.md`, donde siguen
  los 22 `TODO(Matias)` **intactos**. **Completar uno es una violación, no una ayuda**, y
  pausar el benchmark no cambia eso: lo que se sacó del camino es la espera, no la regla.
- **M5 (verify)** — sigue prohibido, con otro motivo: ya no espera un veredicto que no va
  a llegar, sino que nadie midió que valga la pena. Verify es lo más caro de construir y
  el dogfooding no lo desbloquea.
- **Gate humano de M0** — la revisión de ADR-001 por Ismael sigue pendiente, y M1/M2 ya
  se construyeron sobre las cinco capacidades que ese ADR decide. Si la revisión tumba
  una fila, hay código que sobra. **Dejar de esperarla no es darla por cerrada.**

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

**T1 a T5 están hechas y en `main`.** Lo que sigue es qué las cerró y qué quedó abierto.

| Tarea | Estado | Qué la cerró |
|---|---|---|
| T1 — `nightshift audit` | ✅ #4 | `audit` recorre todo lo persistido y afirma que no hay fugas. Encontró una de verdad el 2026-08-27 (#41) y está arreglada. `--min-sessions 5` sigue saliendo 1 por conteo de sesiones (ver abajo). |
| T2 — retrieval por tipo de tarea | ✅ #5 | `general` dejó de puntuar como coincidencia de tipo, y el retrieval se rehace en el primer `UserPromptSubmit` clasificado, sin re-inyectar lo ya dicho. Spec §5.7. |
| T3 — trayectorias huérfanas | ✅ #6 | `SessionStart` cierra las `open` de otras sesiones sin actividad hace más de `orphan_after_hours`. Corte por inactividad, nunca por antigüedad. Spec §5.8. |
| T4 — M3-a dream `consolidate` | ✅ #7 | Agrupación determinista, modelo local sólo para abstraer, salida validada contra esquema + redactor + auditor. Gate: `make dream-selftest`. |
| T5 — M3-b scheduler | ✅ | `launchd` / `systemd` (timer de usuario) / `loop`, con registro de corridas. Gate: `nightshift schedule status` reporta las últimas y sus resultados. |

### Lo que se aprendió mirando el store con el propio plugin

El 2026-08-26 se analizó una sesión real de 252 pasos con `status`, `doctor` y el
auditor. Cuatro cosas que conviene no re-descubrir:

1. **El modo de fallo de nightshift es el silencio.** Capturó 223 pasos vacíos durante
   dos milestones sin que nada lo dijera, porque los hooks salen 0 pase lo que pase y eso
   es correcto. Por eso `doctor` ahora **falla** si la última trayectoria con pasos de
   tool no tiene ninguno con contenido, y `status` reporta calidad de captura. Si tocás
   la captura, mirá esos dos números antes de dar nada por bueno.
2. **Sondeá el payload, no lo supongas.** Los campos reales son `prompt`,
   `tool_response` y `error` (spec §5.9). El replay del selftest usaba nombres inventados
   y por eso pasaba en verde mientras la captura llegaba vacía. Si agregás un hook,
   loguea las claves que llegan de verdad antes de escribir el handler.
3. **Las heurísticas se miden contra trayectorias reales, no se estiman.** La de señal
   decisiva marcaba el 41% de los pasos porque buscaba el comando de test como subcadena:
   un título de PR que dijera `make check` contaba como test que pasa.
4. **Lo que se guarda como resumen es lo que el agente va a leer.** Guardar el
   `tool_response` crudo gastaba el presupuesto de caracteres en `isImage` y
   `noOutputExpected`.

### Antes de nada: ensayá la máquina

```sh
make simulate      # o `nightshift simulate --no-model` si no hay modelo local
```

Corre siete sesiones sintéticas por los siete hooks, audita, cierra una huérfana, hace
las dos pasadas de retrieval, consolida con el modelo, instala el scheduler en un HOME
temporal, corre tres noches simuladas y vuelve a auditar. En un store desechable, en
menos de un minuto. Si algo se rompió, esto lo dice antes de que lo descubras en una
sesión real.

**No cierra ningún gate**, y el motivo está en `LATER.md` §"Sobre el ensayo end-to-end".

### El plan hasta el veredicto

**Reordenado el 2026-08-27** ([PLAN-M4 §2 y §2.5](PLAN-M4.md#25-fase-05--que-s1-sea-s1)):
apareció una fase 0.5 —*que S1 sea S1*— delante del congelamiento del pre-registro,
porque en una sola sesión se encontraron tres defectos en el brazo que M4 mide y los tres
eran invisibles. Las cinco sesiones reales dejaron de ser un trámite en paralelo: son el
instrumento con el que aparecieron. Y [PLAN-M4 §10](PLAN-M4.md#10-preguntas-abiertas--para-responder-o-para-descartar)
tiene ocho preguntas para Matías; descartar una es una respuesta.

[`PLAN-M4.md`](PLAN-M4.md) tiene el detalle: el camino crítico y su orden (por qué la
revisión de ADR-001 va **antes** de congelar el pre-registro), los 22 `TODO(Matias)`
agrupados por lo que desbloquea cada uno, el tamaño real de la corrida de M4 (102 celdas,
~1,1 h medidas), los riesgos con su evidencia, y qué pasa con cada veredicto posible.

### Lo que falta, y de quién es

**Ninguna de estas tres es código pendiente. Son decisiones o evidencia.** Desde el pivot
(§0-bis) **ninguna bloquea**, y las tres siguen abiertas: dejar de esperar algo no es
haberlo obtenido.

1. **El gate de M1: dos sesiones más.** `nightshift audit` no encuentra ninguna fuga en
   el store real, pero hay 3 sesiones distintas capturadas de las 5 que pide el gate.
   Se cierra usando el plugin, no escribiendo código.
   ```sh
   nightshift audit --min-sessions 5
   ```

2. **El gate de M3: tres noches.** El scheduler está y las corridas quedan registradas.
   Falta instalar el timer en la Air y dejarlo correr tres noches seguidas sin
   intervención. Lo hace una persona.
   ```sh
   nightshift schedule install     # toca el gestor de arranque: no lo corre un agente solo
   nightshift schedule status      # a la mañana siguiente
   ```

3. **El gate humano de M0.** La revisión de ADR-001 por Ismael sigue pendiente, y ahora
   hay más código construido sobre las cinco capacidades que ese ADR decide.

### Pausado o prohibido — no empieces

- **M4. Pausado por el pivot (§0-bis), y sigue sin poder correr.** El runner está construido (`nightshift bench`, spec §10.4) y **se niega a
  correr**: `bench/PREREG.md` sigue en borrador con 22 `TODO(Matias)`. **Los tres repos
  fixture también están construidos** (`bench/fixtures/familia-{a,c,d}/`, verificados con
  `make bench-fixtures`). Lo que falta no es código: son los umbrales, el modelo, el seed,
  el protocolo de reset entre corridas, y congelar los identificadores de los fixtures.
  Los fija Matías. Completar un `TODO(Matias)` es una violación, no una ayuda.
  `nightshift bench check` lista los 22 con sección y línea.

  El adaptador que lanza el agente en cada celda también está
  (`bench/agentes/correr-agente.py`) y se niega a correr sin el modelo, el límite de tool
  calls y el protocolo de reset. **Nada de esto se borró al pausar M4**: si el
  pre-registro se congela algún día, M4 corre sin escribir una línea más.

  Un agujero que los fixtures dejan a la vista y no tapan: **en la fila S0 no se pueden
  enumerar las memorias inyectadas** — nightshift no está y las de Auto Memory no son
  visibles. Sin eso la familia D es indecidible, y el runner lo reporta así.
- **M5 (`verify`).** Prohibido. Hoy nada llega a `procedure`, y eso es correcto: ninguna
  memoria inyectada está verificada. El pivot no lo desbloquea — cambia el motivo, no el
  veredicto (§0-bis).
- **Adapter de OpenCode.** Prohibido.

### Si vas a tocar dream

Dos cosas que cuestan tiempo si se redescubren:

- `ollama` re-acomoda las palabras al ancho de la terminal aunque stdout sea un pipe:
  vuelve el cursor con `ESC[nD` y reescribe. Borrar los escapes a secas deja fragmentos
  duplicados y saltos de línea **dentro de strings JSON**. Se usa `--nowordwrap`, y
  `dream.undo_wrapping()` es la red para versiones que no lo tengan.
- `--think false` baja una llamada de 56s a 6s con el mismo modelo.

La agrupación es por tipo de tarea y nada más. Agrupar por firma de herramientas dejaba
grupos de uno, y un grupo de uno no puede tener contradicciones. Agrupar mejor necesita
volumen real, no otra intuición: está en `LATER.md`.

## 4-bis. Lo que cambió el 2026-08-27, y qué mirar primero

Una sesión larga de desarrollo. Lo que hay que saber para no re-derivarlo:

| | |
|---|---|
| **Dream idea y proyecta** ([ADR-004](adr/ADR-004-ideacion-y-proyeccion.md)) | Dibuja el mecanismo como diagrama Mermaid, abstrae desde ahí, y **proyecta** síntomas que nadie observó. Lo proyectado se guarda aparte, pesa exactamente la mitad, y se anuncia como conjetura. Esa frontera es lo que hay que defender: si se borra, esto deja de ser memoria. |
| **Contraste entre implementaciones** ([ADR-005](adr/ADR-005-contraste-entre-implementaciones.md)) | Cuando hay una contradicción registrada, dream consolida **qué cambió, qué compró, qué costó, y cuándo la descartada seguía teniendo razón**. La spec §4.2 lo prometía desde el principio; hasta acá el enlace existía y la precondición no la calculaba nadie. |
| **El presupuesto de M4 es tiempo** (PREREG §2.1) | Decidido por Matías. Medido: 37,8 s por celda de mediana, **1,1 h las 102 celdas**. La factibilidad no es el cuello de botella. |
| **La matriz va repetición → fila** | Para que cortar por presupuesto deje los dos brazos con el mismo n. Con el orden anterior, una corrida cortada era un experimento torcido, no uno más chico. |
| **Los dólares no son una factura** | El CLI reporta a precio de lista (`costBasis: "list"`); con suscripción no se factura. Los tokens son la unidad. Hay un test que falla si alguna línea con `USD` no lo dice. |
| **El retrieval de lo crudo no miraba el prompt** (spec §5.10) | Medido: dos prompts con síntomas distintos devolvían el mismo orden y los mismos scores. Sin abstracción no había enganche por síntoma, así que un síntoma **proyectado** por el modelo pesaba 0.75 y un fallo **observado** pesaba cero. Ahora una trayectoria cruda engancha por los errores de sus pasos `tool_failure`, con el motivo `failure_match`. Sólo fallos: `decisive` marca también los tests en verde, y son el 38% de los pasos. |
| **`consolidation_strategy` era una constante del experimento** | `observed` u `ideate`. Cambia qué **es** el brazo S1: una corrida con una no es comparable con otra. **Desde el pivot ya no es una clave de config** (enmienda 0.3.7): `consolidate` idea siempre. El `TODO(Matias)` de PREREG §2 sigue abierto igual — el default del código no es una decisión de pre-registro. |

### Lo que cambió el 2026-08-27 (tarde), y por qué toca el brazo del benchmark

**El enganche por síntoma no sobrevivía a la paráfrasis, y nadie lo había medido.** La
spec §5.10 verificó que el ranking *discrimina* —dos prompts distintos, órdenes
distintos— pero nunca que aguante que el usuario lo diga con sus palabras, que es la
única forma en que se dice. Medido sobre el store real: **1 de 6 paráfrasis enganchaba.**

La causa era un piso único de dos palabras en común para dos clases de texto que no se
parecen: una oración que el modelo destiló (sin relleno, donde una palabra ya es señal) y
un volcado de error (casi todo andamiaje del harness). Ahora son dos pisos —enmienda
0.3.6, spec §5.10— y ninguna coincidencia puede apoyarse sólo en predicados de fallo
(`falla`, `error`, `bug`), que dicen **que** algo se rompió y no **qué**.

Después: **4 de 6**, con el control negativo en cero las dos veces.

**Esto cambió qué es el brazo `S1`**, y por eso está escrito en tres lados: spec §5.10 +
tabla de enmiendas, `LATER.md`, y `experimentos/05-enganche-por-parafrasis.py`, que es la
medición que lo motivó. PREREG §2 pide que la configuración de retrieval sea una constante
del experimento; el pre-registro sigue en BORRADOR así que el cambio es legítimo, pero
**silencioso hubiera sido exactamente el error que este repo ya documentó** cuando el
ranking cambió tres veces en una sesión sin dejar constancia.

Lo que **no** se arregló y queda medido en `LATER.md`: 2 de 6 paráfrasis siguen sin
enganchar porque no comparten *ninguna* palabra con la frase que las describe —
`resumen`/`memoria consolidada`, `métrica`/`contador de cobertura`. Es sinónimo, no
morfología: `difflib` y el prefijo se probaron y no compran nada. Necesita embeddings,
que chocan con ADR-003, y compite con M5 después del veredicto.

### Y el puntaje de las proyecciones estaba inflado

Decía "seis proyecciones: 2 confirmadas, 2 refutadas, 2 abiertas" en el README, el
README.es y `experimentos/README.md`. **Dos de esas cuentas no existen.** El store tiene
una sola candidata con cuatro proyecciones: **2 confirmadas, 1 refutada, 1 abierta**. La
segunda refutación que se reportaba no está en el store, ni en los logs, ni en ninguna
salida de dream — probablemente era una paráfrasis de memoria de la proyección que
ADR-004 **confirmó** y que produjo `tests/test_suite.py`, con el veredicto dado vuelta.

Se puede contar en una línea, y conviene que la próxima sesión lo haga antes de citar
cualquier número:

```sh
sqlite3 ~/.nightshift/trajectories.sqlite3 \
  "select projected_signals_json from trajectories where status='candidate';"
```

También estaba mal la hora: la corrida que produjo la candidata fue la de **15:25:34Z**;
la de 15:27 produjo **cero**.

### Lo primero que tiene que mirar la sesión que sigue

**La calidad de la captura, no la funcionalidad.** El 2026-08-27 el store real reportaba
**59% de pasos de tool sin contenido**, y la inyección que recibió esta misma sesión
mostraba `(sin resumen)` en los tres pasos decisivos de la trayectoria que le tocó. Es
decir: la máquina entera funciona y le está pasando al agente siluetas sin sustancia.

Es el mismo modo de falla de siempre —el silencio— en su versión más incómoda: ya no
está roto, está *flojo*, y nada falla. `nightshift doctor` y `status` reportan el número.
Empezá por ahí antes que por cualquier feature.

**Y cuando empieces, desglosalo por trayectoria antes de arreglar nada.** Medido después:
el promedio mezcla cohortes. Las trayectorias anteriores al arreglo de los campos del
payload van del 58% al 100% de pasos vacíos; la primera capturada después va **1 de 52,
el 2%**. La captura de hoy trae contenido; lo que no tiene cohortes es la métrica, y una
alarma que suena para siempre es donde se esconde la regresión siguiente. El desglose y
lo que queda sin medir —`Edit` y `Write` no los usó ninguna sesión posterior al arreglo—
están en `LATER.md`.

**Y dos ciclos de sueño sobre 400 pasos de desarrollo real produjeron cero candidatas.**
Se creyó que era el grupo de uno —un día entero es una trayectoria sola y no hay nada
compartido que abstraer— y **ese diagnóstico era falso**. Aislada la variable con el
modelo real: un grupo de una trayectoria **con contenido** sí produce candidata. Lo que
bloqueaba era qué pasos veía el modelo: seis por trayectoria elegidos por la bandera
`decisive`, sin exigirles contenido, y para esa trayectoria los seis salieron vacíos
mientras 177 pasos con texto no se miraban. Arreglado en spec §6.1 (enmienda 0.3.5); el
experimento y la corrección están en `LATER.md`.

Lo del **capítulo** sigue en pie, pero como problema de calidad: de un día heterogéneo
sale una candidata que lo promedia. No está en el plan v0.3.

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
Leé doc/HANDOFF.md entero — empezando por §0-bis, que es el pivot y manda sobre
PLAN-M4.md — después CLAUDE.md y doc/00-spec.md.

El objetivo son las tres ideas: la cadena de pensamiento es la cadena de
ejecución, correrla para adelante (proyectar), e idear antes de razonar. El
gate es `make dogfood`: el agente usando nightshift sobre el código de
nightshift, verificado sobre el store real.

M4, el gate humano de M0 y los gates de M1 y M3 están PAUSADOS: no bloquean y
tampoco están cerrados. No completes ningún TODO(Matias) — pausar el benchmark
no es completar el pre-registro. No empieces M5: nada llega a `procedure` y el
dogfooding no lo desbloquea. Rama propia, gate en verde, PR, y un resumen de
qué quedó en LATER.md.
```
