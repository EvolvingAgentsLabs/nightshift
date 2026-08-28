# Plan — implementar las tres ideas por completo

| Campo | Valor |
|---|---|
| Escrito | 2026-08-28 |
| Reemplaza | nada. Es el plan del pivot de [`HANDOFF.md`](HANDOFF.md) §0-bis |
| Relación con `PLAN-M4.md` | ninguna: ese plan está **pausado** y este no lo reabre |
| Alcance | qué le falta a cada una de las tres ideas para estar entera, y en qué orden |
| Gate del plan | `make dogfood` en cada fase, más el gate propio de cada una |

## 0. Qué pregunta responde este plan

El pivot del 2026-08-27 fijó tres ideas como objetivo. Las tres **tienen mecanismo en el
código y ninguna está entera.** Este plan dice, para cada una, qué falta exactamente,
cómo se comprueba que dejó de faltar, y en qué orden conviene hacerlo.

Y hay un hallazgo del 2026-08-28 que ordena todo lo demás, así que va primero.

### El hallazgo que ordena el plan

`nightshift sleep` consolidó la sesión en la que se arregló un bug de una línea
(`evidence or MARCA`, un `or` que descartaba el marcador cuando la evidencia existía). La
candidata `1f94f424` lo abstrajo así:

> «Una propiedad derivada del paso viaja como **bandera efímera** calculada en el momento
> de la captura, en vez de recalcularse desde el dato persistido. Cuando el registro se
> reescribe al sellar, la bandera no viaja…»

**Ese mecanismo no existe.** No hay ninguna bandera por paso. La candidata tiene diagrama,
analogía, señal decisiva y cinco precondiciones coherentes, y describe un sistema que no es
éste. Y su `hypothesis` —«se creyó que la redacción alteraba el texto del comando»— es
inventada: nadie creyó eso, y el prompt pide explícitamente `null` cuando no se puede
inferir ninguna.

Es exactamente lo que [`../LATER.md`](../LATER.md) ya dice de sí mismo: *«una explicación
plausible anotada como hallazgo es exactamente el tipo de memoria que este proyecto dice no
querer»*. Sólo que esta vez la escribió el modelo.

**No es un bug del sistema.** Está marcada `candidate`, se inyecta con menos peso y dice
«SIN VERIFICAR» en cada línea. Que una candidata sea falsa es la razón por la que nada llega
a `procedure`. Lo que sí es un agujero es que **nada en el plugin puede decir que es
falsa**, y por eso va a seguir enganchando con las palabras `bandera efímera` para siempre.

## 1. Estado real, medido

Del store real, hoy, contado y no estimado:

```sh
sqlite3 ~/.nightshift/trajectories.sqlite3 \
  "select substr(id,1,8), (diagram is not null), (hypothesis is not null),
          json_array_length(projected_signals_json)
   from trajectories where status='candidate';"
```

| Candidata | Diagrama | Hipótesis | Proyecciones | Resueltas |
|---|---|---|---|---|
| `fff6af83` | no (anterior a ADR-004) | sí | 4 | **0** |
| `cbbd7ff0` | sí | sí | 5 | **0** |
| `5b3ff97f` | sí | sí | 5 | **0** |
| `1f94f424` | sí | sí (**inventada**) | 5 | **0** |

**4 candidatas, 19 proyecciones, 0 resoluciones registradas en el store.** Las de
`cbbd7ff0` se resolvieron a mano y el veredicto vive en `../LATER.md`, en prosa, sin
ninguna forma de que el retrieval lo sepa.

`make check` pasa con 318 tests. `make dogfood` pasa. Nada llega a `procedure`.

## 2. Las tres ideas, una por una

### Idea 1 — CTE: la cadena de pensamiento es la cadena de ejecución

**Construido.** Siete hooks capturan comando, fallo, corrección y desenlace. El redactor
es determinista. `decisive` se lee del comando guardado y no de una bandera. Una corrección
enlaza con el paso que corrigió (`contradicted`). El capítulo se puede sellar a demanda.

**Lo que falta para decir que está entera:**

- **G1.1 — El primer eslabón se inventa.** La spec llama a `hypothesis` «el primer eslabón
  de la cadena causal». Hoy la escribe el modelo sin ninguna atadura al material: el prompt
  pide `null` cuando no se puede inferir, `validate` sólo la revisa por fugas, y el
  2026-08-28 el modelo escribió una hipótesis que nadie tuvo. Una cadena causal cuyo primer
  eslabón es ficción no es una cadena de ejecución: es una historia.
- **G1.2 — La cadena no tiene eslabones.** Los pasos son una lista plana más dos banderas.
  `hipótesis → comando → error → corrección → señal decisiva → fix` está afirmado en el
  README y en la spec y **no es una estructura de datos**: `why` los imprime en orden y no
  puede decir qué corrección arregló qué error. La cadena está implícita en el orden, que es
  la forma más débil de tenerla.
- **G1.3 — El capítulo lo detecta una persona.** `sleep` resolvió el borde; detectarlo no.
  Queda fuera de este plan a propósito, y §5 dice por qué.

### Idea 2 — Correr la cadena para adelante

**Construido.** Las proyecciones se guardan aparte (`projected_signals_json`), pesan
exactamente la mitad, se anuncian como conjetura en cada lugar donde aparecen, enganchan
con el prompt por paráfrasis, y desde la enmienda 0.3.7 **ordenan antes** que cualquier
puntaje sin enganche. Una conjetura llega al agente antes de que el error ocurra.

**Lo que falta, y es el agujero más grande del proyecto:**

- **G2.1 — Nada resuelve una conjetura.** 19 proyecciones, 0 resoluciones. No hay columna,
  no hay comando, no hay forma de que el store sepa que algo se confirmó o se refutó.
  [`../experimentos/preguntar.py`](../experimentos/preguntar.py) abre la base en **sólo
  lectura** y escribe el veredicto a un JSONL afuera, a propósito, porque era un
  experimento. El propio README lo dice: *«una conjetura que nadie resuelve no es memoria,
  es una nota»*.
- **G2.2 — Sin tasa de acierto, la mitad del peso es una postura.** `W_PROJECTED_MATCH =
  W_SIGNAL_MATCH / 2` está fijado por un test y defendido por ADR-004 como jerarquía de
  evidencia, no como calibración. Está bien que sea así **mientras nadie pueda medirlo**.
  Con resoluciones se puede medir, y entonces el número deja de ser una postura.
- **G2.3 — Una conjetura refutada sigue enganchando igual que una confirmada.** Hoy el
  ranking no distingue las tres situaciones —confirmada, refutada, abierta— porque las tres
  son el mismo dato.

### Idea 3 — Idear en vez de razonar

**Construido.** `IDEATE_PREFIX` es incondicional desde la enmienda 0.3.7: no hay clave de
config que lo apague. El modelo devuelve `diagram` (Mermaid) y `mechanism`, los dos se
persisten, pasan por el redactor y el auditor, y el diagrama se inyecta **entero** dentro
de un bloque ` ```mermaid `. Tres de las cuatro candidatas tienen dibujo.

**Lo que falta:**

- **G3.1 — El diagrama no se valida como diagrama.** `validate` sólo lo revisa por fugas.
  Un Mermaid roto —un corchete sin cerrar, una arista a un nodo que no existe— entra tal
  cual al contexto del agente dentro de un bloque que promete renderizar. Un dibujo roto es
  peor que ninguno: ocupa el lugar del dibujo y no dice nada.
- **G3.2 — Nadie midió que idear sirva.** ADR-004 se aceptó con n=1 y lo dice. Desde
  entonces idear pasó a ser el flujo único, así que la apuesta central del proyecto —*el
  dibujo de un mecanismo es invariante entre síntomas de un modo que la prosa no lo es*—
  sigue sin control. El brazo de control existe
  ([`../experimentos/ideate.py`](../experimentos/ideate.py)) y no se corrió desde el cambio.
- **G3.3 — El costo está medido y el beneficio no.** Casi el triple de tokens de salida por
  grupo (1.715 → 4.866). Un costo medido contra un beneficio afirmado no es un trade-off,
  es una preferencia.

## 3. El README: qué dice hoy y qué es falso

Revisado línea por línea contra el estado del 2026-08-28.

| Dónde | Qué dice | Estado |
|---|---|---|
| Bloque de estado (L10-14) | «The code is no longer what blocks the benchmark: the **evidence** is» | **Falso desde el 2026-08-27.** `PLAN-M4.md` §0 ya lo desmintió el mismo día, y el pivot lo sacó del camino crítico |
| Bloque de estado | «M1's gate is five real sessions, M3's is three unattended nights» | **Desactualizado.** Los dos siguen abiertos y **ya no bloquean**. El gate es `make dogfood` y el README no lo nombra |
| Bloque de estado | No menciona el pivot | **Falta.** El objetivo del proyecto cambió y el README describe el anterior |
| «The three ideas» (L43-69) | La descripción de las tres | **Correcta y buena.** Le falta decir que idear es **incondicional** desde 0.3.7, y que un enganche **ordena antes** que el puntaje |
| «The night it dreamed about itself» (L127) | «four projections: two confirmed, one refuted, one open» | **Incompleto de una forma peligrosa.** Es el marcador de *una* candidata y se lee como el marcador del proyecto. Hoy hay **4 candidatas y 19 proyecciones**, y las de `cbbd7ff0` se resolvieron. Es el número exacto que este repo ya publicó mal una vez |
| «The honest part» (L159-167) | El benchmark «has never run, because the pre-registration is still a draft» | **Cierto pero incompleto.** No dice que M4 está pausado, y linkea `PLAN-M4.md` como «the plan» cuando ese documento empieza con un banner de pausa |
| «Run it» (L90-97) | `init` y `claude --plugin-dir .` | **Falta `make dogfood`**, que es el gate, y `nightshift sleep`, que sólo aparece en la tabla de skills |
| Tabla de skills | Incluye `/nightshift:sleep` | **Al día** |
| «The defect… paraphrase» (L139-157) | 1 de 6 → 4 de 6 | **Al día** |
| Matriz A–E | E es «no — this is M5» | **Al día**, y sigue siendo lo más importante que dice |

`README.es.md` tiene los mismos problemas: es traducción, no un documento aparte.

**Una restricción técnica que hay que respetar al reescribir:** `tests/test_readme.py`
afirma que la línea que empieza con `> **Status:` contiene el milestone de
`nightshift.__version__` (`0.1.0-M3`). El pivot no avanzó el milestone, así que la línea
sigue diciendo M3 y el `__version__` no se toca. Cambiarlo es una decisión de Matías, no
una limpieza.

## 4. El plan

Cinco fases. Cada una termina en commit medible con su gate, y ninguna depende de una
decisión humana pendiente.

### F0 — El README dice lo que el proyecto es (medio día)

Va **primero**, no último, por el motivo que este repo ya documentó dos veces: un README
que miente es más caro que uno incompleto, y el de hoy afirma un camino crítico que fue
abandonado.

- Reescribir el bloque de estado: el pivot, `make dogfood`, y qué **no** dice ese gate.
- «The three ideas»: idear es incondicional; un enganche ordena antes que el puntaje.
- Sacar el marcador de proyecciones de la prosa y dejar **el comando que lo cuenta**, con
  una foto fechada al lado. Un número escrito a mano en dos idiomas se desincroniza; ya
  pasó.
- `make dogfood` y `nightshift sleep` en «Run it».
- «The honest part»: M4 pausado, con el link diciendo que está pausado.
- Espejar todo en `README.es.md`.

**Gate:** `make check` (`test_readme.py` verifica comandos, flags, rutas y afirmaciones que
caducan) + un test nuevo: **ninguno de los dos README puede afirmar un marcador de
proyecciones en prosa**. La fuente es el store, y el README cita el comando.

### F1 — Resolver conjeturas (idea 2) — el corazón del plan

Cierra el único bucle que hoy no cierra, y es la precondición para medir cualquier otra
cosa.

1. **Modelo de datos.** Tabla `projections` por migración: `trajectory_id`, `idx`, `text`,
   `status` (`open` · `confirmed` · `refuted`), `resolved_at`, `evidence`, `resolved_by`.
   Se migra desde `projected_signals_json`, que **no se borra**: es el dato original y el
   esquema `trajectory.v1` lo define.
2. **`nightshift resolve`.** Lista las abiertas y las resuelve. Con flags para que sea
   scriptable (`--projection <id> --confirmed --evidence "…"`) y un modo interactivo
   adaptado de `preguntar.py`, que deja de ser experimento y pasa a ser comando.
   `--refuted` **exige** evidencia: refutar sin motivo es olvidar con otro nombre.
3. **El retrieval las distingue.** Una refutada deja de enganchar. Una confirmada **sigue
   pesando la mitad** —confirmarla no la convierte en observación, y esa frontera es lo que
   ADR-004 defiende— pero se anuncia como «anticipada y después confirmada por una
   persona», que es una tercera categoría y no un ascenso.
4. **`status` reporta la tasa de acierto.** Confirmadas / resueltas, con las abiertas
   contadas aparte. Es el número que el README necesita y que hoy nadie tiene.
5. **El auditor lo defiende.** `audit` falla si una proyección resuelta perdió su evidencia,
   por el mismo motivo por el que falla ante una fuga.

**Gate:** `make check` con tests que fallen si una refutada vuelve a enganchar, si una
confirmada sube de peso, o si `resolve --refuted` acepta evidencia vacía. Más
`make dogfood`. Más las **19 proyecciones del store real resueltas o marcadas abiertas a
mano**, que es dogfooding y no test.

### F2 — No toda línea capturada es evidencia (idea 1)

**Corregida el 2026-08-28, antes de escribir una línea de código.** La primera versión de
esta fase decía: anclar cada afirmación a un índice de paso, y si el índice no existe,
descartarla. **Se midió sobre el único caso conocido de fabricación y no habría atrapado
nada.** Los pasos de `1f94f424`:

```
paso 4  run_shell  "308: # ahora del comando guardado (_es_comando_de_test), sin
                    bandera de por medio. La spec §4.3…"
paso 5  run_shell  "El comando está redactado, y eso no lo afecta: el redactor toca
                    rutas, secretos e identificadores…"
```

El modelo no inventó de la nada: levantó **el razonamiento ya escrito en los comentarios
del código** y lo presentó como diagnóstico del bug. «Sin bandera de por medio» —un
comentario sobre un diseño viejo y ya cambiado— se convirtió en «una propiedad viaja como
bandera efímera». «El comando está redactado y eso no lo afecta» se convirtió en la
hipótesis «se creyó que la redacción alteraba el texto». Cada elemento del dibujo ficticio
**rastrea a un paso real**, así que el anclaje pasaba.

La distinción que sí discrimina es otra, y es más barata:

> ¿este paso es una **observación** de lo que pasó, o es el repositorio **hablando de sí
> mismo**?

Un `tool_failure`, un test en rojo, una corrección del usuario son evidencia de esta
sesión. La salida de un `grep`, de un `cat`, de un `sed -n` es el repo explicando un diseño
que puede ser viejo, ajeno o ya revertido. Hoy `pasos_para_el_prompt` los ordena —fallos
primero— pero los entrega todos con el mismo rango.

1. **Clasificar el paso por lo que es.** Observación (fallo, test, corrección, desenlace)
   contra lectura (leer archivos, buscar en el repo, listar). Determinista, del comando
   guardado, como `_es_comando_de_test`.
2. **El prompt lo dice.** Las lecturas van etiquetadas como contexto del repositorio, no
   como evidencia de la sesión, con la instrucción explícita de que un comentario del
   código **no** es una observación sobre este trabajo.
3. **El anclaje, ahora sí, sobre observaciones.** `hypothesis` cita el índice de un paso
   **de observación**, o es `null`. Sobre lectura no vale.

**Gate:** `make check`, con la clasificación medida contra los pasos reales del store —no
estimada— y un test de replay que rechace una hipótesis anclada a una lectura.

### F3 — El dibujo tiene que ser un dibujo (idea 3)

1. **Validar el Mermaid.** Con stdlib, sobre el subconjunto que el prompt pide
   (`flowchart`, `sequenceDiagram`, `stateDiagram-v2`): cabecera reconocida, corchetes y
   paréntesis balanceados, toda arista referida a un nodo declarado, tope de diez nodos
   —que hoy sólo se pide en el prompt— y ningún backtick suelto que rompa el bloque al
   inyectarlo.
2. **Rechazo → reintento.** El bucle de reintentos de `consolidate` ya existe y ya sabe
   devolverle al modelo por qué se lo rechazó. Un diagrama roto entra por ahí, como una
   fuga.
3. **Fixtures.** Diagramas válidos e inválidos en `schema/examples/`, como el resto: el
   gate `validate-schema` ya recorre ese directorio.

**Gate:** `make check` con los fixtures. Un diagrama roto no puede llegar a `candidate`.

**Y lo que esta fase NO responde**, dicho acá porque es fácil dejarlo implícito: la validez
sintáctica contesta *«¿va a renderizar?»*, nunca *«¿es cierto?»*. El dibujo de `1f94f424` es
Mermaid perfectamente válido y describe un mecanismo que no existe. Para eso está F2, y
sobre todo §7.

### F4 — Medir la apuesta (idea 3)

La única fase que puede **falsificar** el proyecto, y por eso va después de F1: sin
resoluciones, comparar los dos brazos es comparar dos textos que suenan bien.

1. Correr `experimentos/ideate.py` sobre las trayectorias cerradas del store real, los dos
   brazos, mismo modelo, misma semilla de corpus.
2. Comparar lo que importa y no lo que impresiona: **cuántas proyecciones de cada brazo se
   pueden resolver**, y de ésas cuántas se confirman. Un brazo que proyecta cinco cosas
   incomprobables pierde contra uno que proyecta dos comprobables.
3. Escribir el resultado **aunque no favorezca a idear**. `experimentos/` ya tiene
   experimentos cuyo resultado no favorece al plugin; es la única razón por la que los
   demás valen algo.

**Gate:** un experimento reproducible con su salida commiteada, y ADR-004 actualizado con
el n real. Si el resultado es negativo, la decisión de qué hacer es de Matías: el
experimento no la toma.

### F5 — El README, otra vez

Después de F1–F4 el README vuelve a estar desactualizado, y esta vez para bien. Una pasada
corta: la tasa de acierto de las conjeturas, el resultado de F4 sea cual sea, y el marcador
A–E revisado. `README.es.md` en el mismo commit, siempre.

## 7. Oráculos — cerrar el bucle que las proyecciones abren

**No es una cuarta idea suelta: es el cierre de la idea 2.** Proyectar abre un bucle —19
conjeturas hoy— y nada lo cierra. Un oráculo es exactamente lo que lo cierra, y F1 es un
caso particular: pone al humano de oráculo. Esta sección generaliza **quién** puede serlo.

El objetivo, dicho como lo pidió Matías el 2026-08-28: incorporar CoT, CoT de imaginación
y CTE **generados afuera** al mecanismo de sueño, con influencia de un oráculo externo, para
agregar comportamiento que el modelo no produce solo.

Y la restricción que ordena todo el diseño: **el oráculo es un comando, no un servicio.**
ADR-003 prohíbe red desde `nightshift/` y una API key nueva. El mismo patrón que ya usa el
modelo —`subprocess`, stdin, stdout— sirve para un humano, un script, un modelo distinto o
una API que envuelva el usuario, sin comprometer al proyecto con ninguno.

### O1 — El oráculo que ya está escrito y nadie lee

`hook.py` registra cada inyección con `into_trajectory`: **qué memoria entró a qué
trayectoria.** Esa trayectoria después se cierra con un desenlace. La arista existe, está
poblada, y `grep into_trajectory nightshift/` da **un solo uso**: el `INSERT`.

```
memoria inyectada    veces   cómo terminó quien la recibió
8347ad4f               2     tests_passed
a49c1582               3     unknown, tests_passed
cbbd7ff0               1     tests_passed
fff6af83               2     tests_passed
```

Es externo al modelo, determinista, gratis, y es literalmente «reforzar la ejecución».

**Se reporta, no se rankea.** Tres motivos y ninguno es prudencia genérica:

- Es **correlación**. No dice que la memoria haya servido: eso es el contrafáctico que M4
  iba a medir, y M4 está pausado.
- **n = 10 inyecciones.** Alcanza para una columna en `status`, no para un peso.
- El riesgo específico es un **bucle que se retroalimenta**: una memoria que sube de puntaje
  por haber caído en una sesión verde se inyecta más, cae en más sesiones verdes y domina
  para siempre. Un ranking que se alimenta de su propia salida deja de medir el repo y pasa
  a medirse a sí mismo.

Convertirlo en peso es una decisión de Matías, con el número puesto por él.

### O2 — El oráculo de git: ¿el fix sobrevivió?

Sin modelo, sin red, sin credencial. Sobre el `base_commit` que la trayectoria ya guarda:
¿el commit se revirtió?, ¿los archivos que tocó se volvieron a tocar poco después?, ¿el
test que se agregó sigue existiendo? Es lo más parecido a verificación que se puede tener
sin M5, y es completamente externo al modelo.

**No es `verify` y no hay que llamarlo así.** `verify` (ADR-002) reproduce una trayectoria
contra un gate declarado; esto lee historia. Una candidata que sobrevivió no queda
verificada: queda **corroborada**, que es una tercera categoría y no un ascenso.

### O3 — `oracle_command`: el oráculo genérico

Un ejecutable configurable que lee una pregunta por stdin y escribe un veredicto por
stdout, con el mismo contrato que `model_command`. Con eso, F1 (el humano), O2 (git) y
cualquier oráculo futuro son el mismo mecanismo con distinto ejecutable.

Va con **ADR-006**, porque decide algo que ADR-003 no había decidido: hasta dónde llega
«sin dependencias remotas» cuando el usuario enchufa su propio ejecutable. La respuesta
propuesta: nightshift no habla con la red **nunca**; lo que haga el comando del usuario es
del usuario, y el store deja constancia de qué oráculo respondió.

### O4 — `import`: CTE y CoT generados afuera

`nightshift export` emite `trajectory.v1`. **No hay `import`.** La plomería es fácil; lo
que no es fácil es lo otro:

- **Procedencia.** Una trayectoria importada no se observó acá, el redactor no corrió sobre
  ella acá, y nada de lo que afirma es comprobable desde esta máquina. Si entra al mismo
  pool con los mismos pesos, la jerarquía observado > inferido > conjeturado —lo único que
  este proyecto defiende de verdad— se colapsa. Necesita una **clase de origen** propia,
  igual que `projected_signals` es una clase aparte de `signals`.
- **Un CoT externo no es un CTE.** No ejecutó. Importar un CoT como si fuera cadena de
  ejecución es el modo de falla de `1f94f424` institucionalizado. Entra etiquetado como lo
  que es —una sugerencia— o no entra.

**Decisión de Matías, no de un agente: cuánto pesa lo externo.** Es la misma clase de
decisión que `W_PROJECTED_MATCH`. El default que se implementa —y que él cambia con un
número— es el único que no puede romper nada: **lo externo pesa estrictamente menos que lo
propio y nunca puede desplazar a una observación de esta máquina.**

### Qué queda descartado

Un oráculo **remoto** llamado por nightshift. Choca de frente con ADR-003 y no lo
desbloquea este plan: si alguna vez hace falta, entra envuelto en un `oracle_command` que
escribe el usuario, con su credencial y su riesgo.

## 5. Qué no entra en este plan, y por qué

- **Detectar el capítulo solo (G1.3).** `sleep` puso el borde donde lo pone una persona.
  Automatizarlo antes de medir si esos bordes producen candidatas mejores que un día entero
  sería estimar en vez de medir, que es el error que `../LATER.md` documenta tres veces. F1
  produce justamente ese dato.
- **G1.2, la cadena con eslabones explícitos.** Es un cambio de esquema grande y hoy no
  tiene un síntoma medido que lo pida. Va a `../LATER.md` con su motivo.
- **M5 (`verify`).** Sigue prohibido. F1 se le parece —resolver una conjetura es
  verificarla— y no es lo mismo: `verify` reproduce una trayectoria contra un gate
  automático, F1 registra el juicio de una persona sobre una conjetura. Confundirlos sería
  llamar verificado a algo que no lo está.
- **Reabrir M4.** Pausado. Ninguna fase de este plan lo necesita ni lo desbloquea.
- **Embeddings para las dos paráfrasis que no enganchan.** Chocan con ADR-003. Sin cambio.

## 8. El ciclo de trabajo: una hipótesis por archivo

**Agregado el 2026-08-28, a pedido de Matías.** El plan de arriba dice qué falta; esto lo
vuelve una cola que se puede recorrer sin releerlo.

```sh
nightshift experiments              # las 21
nightshift experiments --only H03   # una
```

Cada hipótesis vive en `experimentos/hipotesis/H<nn>-*.py`, corre sola, y devuelve
`PASS`, `FAIL` o `BLOCKED`. **Los tres estados son tres y no dos**: `BLOCKED` es una
hipótesis que no se puede comprobar todavía porque espera una decisión humana o material
que no existe, y leerla como `FAIL` convierte una espera en un fracaso.

Así, cada hipótesis pendiente es una tarea con borde: se le puede dar a un subagente sin
más contexto que su archivo, porque el detalle del `FAIL` dice qué falta **y por qué no
está**.

### El estado al escribir esto

**15 de 21 comprobadas · 5 sin implementar · 1 esperando.**

| | Hipótesis pendiente | Qué es |
|---|---|---|
| H04 | La cadena tiene eslabones explícitos | G1.2 — los pasos son una lista plana con dos banderas |
| H06 | El capítulo se detecta solo | G1.3 — el borde lo pone una persona, y conviene medir antes de automatizar |
| H17 | Idear produce conjeturas más resolubles que no idear | **BLOCKED**, no `FAIL`: es F4 y cuesta llamadas reales al modelo |
| H19 | Git dice si el fix sobrevivió | O2 |
| H20 | Hay un oráculo genérico (`oracle_command`) | O3 |
| H21 | Se puede importar un CTE externo | O4, y cuánto pesa lo externo lo decide Matías |

### La iteración

1. `nightshift experiments` — qué falta hoy.
2. Trabajar los `FAIL`, uno por rama, con su gate.
3. Cerrar la sesión y `nightshift sleep`, para que lo que se hizo entre a la memoria del
   propio proyecto.

El paso 3 no es ceremonia: es la única forma de que el plugin acumule material sobre su
propio desarrollo, que es el gate del pivot.

## 6. Cómo se sabe que cada idea quedó entera

Un criterio por idea, y los tres son comprobables sin preguntarle a nadie:

| Idea | Entera cuando |
|---|---|
| CTE | `why` puede mostrar el primer eslabón de la cadena **anclado a un paso real**, o decir que no hay hipótesis. Ninguna candidata nueva trae una hipótesis que no se pueda ubicar |
| Correr la cadena para adelante | Toda proyección del store tiene estado, `status` reporta la tasa de acierto, y una refutada dejó de enganchar |
| Idear en vez de razonar | Ningún diagrama inválido llega a `candidate`, y el experimento de control tiene un resultado escrito — favorable o no |

Y una condición que vale para las tres: **`make dogfood` en verde después de cada fase**,
sobre el store real y no sobre uno desechable.
