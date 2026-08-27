# Experimentos

Tres experimentos que se corren solos y muestran qué hace nightshift que la memoria
declarativa nativa no hace. Están escritos para reproducirse, no para convencer: dos de
los tres dieron resultados que **no favorecen al plugin**, y están reportados igual.

Todos corren sobre copias desechables y stores desechables. **Ninguno toca tu store ni
suma al conteo del gate de M1.**

| | Qué muestra | Cuesta |
|---|---|---|
| [01](01-mismo-bug-otra-cara.sh) | El mismo bug con otra cara: qué transfiere, la traza o el patrón | 6 sesiones de agente + 1 dream |
| [02](02-lo-descartado-no-se-pierde.sh) | Lo que se descartó sobrevive enlazado, con su precondición | 1 dream |
| [03](03-cinco-ciclos-sobre-si-mismo.sh) | Cinco ciclos del plugin sobre sus propios problemas | 5 sesiones + 5 dreams |
| [04](04-ideacion-visual.sh) | Un bloque `ideate` antes de abstraer: ¿el dibujo transfiere mejor que la prosa? | 6 sesiones + 2 consolidaciones |
| [preguntar](preguntar.py) | Lo proyectado, presentado como opciones para que una persona lo resuelva | nada: lee el store y pregunta |

```sh
./experimentos/01-mismo-bug-otra-cara.sh          # CONSERVAR=1 para no borrar el trabajo
./experimentos/02-lo-descartado-no-se-pierde.sh
./experimentos/03-cinco-ciclos-sobre-si-mismo.sh
./experimentos/04-ideacion-visual.sh
python3 experimentos/preguntar.py --dry-run       # sin --dry-run, pregunta
```

---

## 01 — El mismo bug con otra cara

**La capacidad que ilustra:** memoria procedimental (A). La declarativa guarda *qué es
verdad*; la procedimental, *cómo se averiguó*.

**El montaje.** Dos tareas del repo fixture de la familia A. Comparten causa —una función
decide qué significa "la misma clave" y no saca los caracteres invisibles— y no comparten
síntoma:

- `test_01_indice`: `buscar()` levanta `KeyError` con una clave que está en el índice.
- `test_09_reporte`: los totales no cierran, el mismo cliente aparece dos veces.

Un hecho declarativo —*"el bug estaba en `texto.py`"*— no sirve para el segundo: el
archivo es otro y el síntoma también. Un procedimiento —*"cuando dos claves idénticas a
la vista no matchean, mirá los invisibles en el normalizador"*— sirve las dos veces.

**Tres filas, y la del medio es la trampa:**

| Fila | La segunda sesión recibe |
|---|---|
| `sin-memoria` | nada |
| `memoria-cruda` | los **pasos** de la primera, sin consolidar |
| `memoria-soñada` | el **patrón** que dream extrajo |

La fila del medio existe porque inyectar la traza cruda es gastar contexto en los pasos de
otro problema. La tesis del proyecto es que lo que transfiere es la abstracción, no el
rastro.

### Lo que dio (2026-08-26, `sonnet`)

```
fila            tarea            resuelto  tool_calls
sin-memoria     test_01_indice   sí        8
sin-memoria     test_09_reporte  sí        15
memoria-cruda   test_01_indice   sí        13
memoria-cruda   test_09_reporte  sí        18
memoria-sonada  test_01_indice   sí        10
memoria-sonada  test_09_reporte  sí        16
```

Tres cosas, y la primera es la que importa:

**1. El ruido se come el efecto.** Las tres primeras filas son *la misma tarea sin ninguna
memoria disponible* —el store está vacío cuando corre— y dieron 8, 13 y 10 tool calls. La
varianza entre corridas idénticas es más grande que cualquier diferencia entre filas. Con
n=1 por celda este experimento **no puede distinguir nada**, y por eso `bench/PREREG.md`
pide tres corridas por celda y umbrales fijados de antemano.

**2. La maquinaria funciona.** La memoria se inyectó, y la diferencia entre las dos filas
con memoria se ve en qué recibieron:

```
memoria-cruda:   ← f430c6c4 [closed]    score=1.05  sin patrón: se le pasan 14 pasos crudos
memoria-soñada:  ← 81db8dde [candidate] score=2.10  patrón: El índice se construye
                   aplicando una normalización a la clave, pero la consulta busca con la
                   clave cruda…
```

El peso de la `candidate` duplica al de la trayectoria cruda, que es lo que la spec §6.3
manda.

**3. Con una sola trayectoria, dream abstrae *ese* caso, no la causa compartida.** El
patrón de arriba describe el bug del índice, no la regla que sirve para los diez síntomas.
La familia A tiene diez bugs con una causa justamente para que el patrón salga de varios;
consolidar desde uno da un patrón fiel y poco portable. Está anotado en `LATER.md`.

**Lo que este experimento no demuestra:** que nightshift sirva. Seis sesiones no son
evidencia. Eso lo decide M4.

---

## 02 — Lo que se descartó no se pierde

**La capacidad que ilustra:** alternativas descartadas con precondiciones (B). Auto Dream
**borra** lo contradicho; nightshift lo conserva enlazado.

**El montaje.** Tres sesiones sobre el mismo problema:

1. Se prueba subir el límite de tiempo a 30 s. El usuario corrige: *"eso tapa el problema,
   no lo arregla"*. La trayectoria cierra como `user_corrected`.
2. Otra sesión encuentra que el llamador pasaba `timeout=None` y lo hace leer el límite
   configurado. Cierra como `tests_passed`.
3. Dream consolida las dos.

### Lo que dio

```
  cc11645b  superseded  user_corrected  superseded_by 461ebd39
  461ebd39  candidate   tests_passed

  trayectorias en el store: 2. La contradicha NO se borró.
```

Y `nightshift why` sobre la descartada reconstruye los dos lados:

```
trayectoria cc11645b…
  estado        : superseded
  desenlace     : user_corrected
contradicha por 461ebd39 — esta trayectoria sobrevive enlazada, no se borró.
  `/nightshift:why 461ebd39` muestra la sucesora.
```

**Por qué importa.** Dentro de tres semanas, alguien va a proponer subir el timeout otra
vez. La memoria declarativa no tiene nada que decir: el hecho *"el timeout está en 2000"*
es verdadero y no ayuda. La procedimental tiene la trayectoria completa: se probó, quién
la contradijo, y con qué se resolvió en su lugar.

Una alternativa descartada **sin** su precondición es ruido. Con ella, es conocimiento —
por eso `valid_when` existe y por eso la trayectoria vieja no se borra.

---

## 03 — Cinco ciclos del plugin sobre sí mismo

**Qué es.** Cinco sesiones reales de Claude Code sobre una copia de este repositorio, con
el plugin cargado y capturando. Entre ciclo y ciclo corre dream. Cada ciclo ataca un
problema abierto distinto de `LATER.md`, y arranca con lo que dejaron los anteriores.

Los cinco problemas, todos reales y todos anotados antes de correr:

1. `status` no dice cuánto ocupa el store, y la política de retención está diferida
   justamente porque no hay con qué medir.
2. `schedule status` no dice cuándo es la próxima corrida.
3. `dream` no tiene tope de grupos por corrida, y desde ADR-003 cada grupo cuesta dinero.
4. `why` no dice cuánto costó consolidar una candidate ni con qué modelo.
5. `bench report` no distingue una celda que falló de una que no llegó a terminar.

**Qué mirar:** si lo inyectado en el ciclo N sirvió en el N+1, y qué tan bien abstrae
dream cuando el grupo crece de una trayectoria a cuatro — que es exactamente el límite que
encontró el experimento 01.

**Lo que no es.** Sesiones dirigidas por un script no son sesiones de una persona
trabajando. Corren sobre una copia y un store propios, así que **no suman al conteo del
gate de M1**, que pide cinco sesiones reales. Los resultados de esta corrida están más
abajo, y los cambios que sobrevivieron entraron al repo por el camino normal: rama, gate
en verde, PR.

### Lo que dio (2026-08-26, con `sonnet`)

```
ciclo  problema                  tool_calls  archivos  make_check  inyecciones
1      medir el store            42          5         OK          0
2      próxima corrida           26          7         OK          1
3      tope de grupos en dream   28          10        OK          2
4      trazabilidad del costo    40          10        OK          3
5      celdas que no terminaron  48          12        OK          4
```

**Los cinco dejaron el gate en verde y produjeron código que se pudo mergear**: 431
líneas, de las cuales 282 son tests. Las cinco features funcionan:

```
store: ~/.nightshift/trajectories.sqlite3 (1.3 MB en disco)
próxima    : 2026-08-27 03:30
--max-groups MAX_GROUPS
  consolidada con: claude -p --output-format json
```

Tres cosas que se leen en la tabla:

**Las inyecciones crecen de 0 a 4.** Cada ciclo recibe lo que consolidaron los anteriores:
el 1 arranca con el store vacío, el 5 con cuatro patrones.

**Los tool calls no bajan.** 42 → 26 → 28 → 40 → 48. Los cinco problemas no son igual de
difíciles y los archivos tocados crecen de 5 a 12, así que la serie no dice nada sobre si
la memoria ayudó. Es el mismo límite que encontró el experimento 01, otra vez: sin
corridas repetidas de la misma tarea, no hay con qué comparar.

**La calidad alcanzó para mergearlo.** El ciclo 4 usó el mecanismo de migración del
esquema que se había construido horas antes, agregó ahí sus columnas y subió la revisión,
sin que el prompt se lo pidiera. Su docstring distingue "el backend no reportó costo" de
"costó cero", que es la misma distinción que hace el código de al lado. El trabajo entró
al repo por el camino normal: rama, `make check` en verde, PR.

**Lo que estos cinco ciclos no son:** sesiones de una persona trabajando. Corrieron sobre
una copia y un store propios, y **no suman al conteo del gate de M1**.

---

## 04 — Un bloque `ideate` antes de abstraer

**De dónde sale.** De una idea de Matías: antes de razonar, **idear** — describir el
mecanismo como lo hace una persona, en imágenes. Un diagrama, una escena, dos cuadros de
animación. Cómo un algoritmo recorre el área bajo una curva; cómo un banco de filtros
deforma una señal; qué le pasa a un dato al atravesar una función.

**La hipótesis, que se puede falsar:** *el dibujo de un mecanismo es invariante entre
síntomas de un modo que la prosa no lo es.* Si vale, una abstracción hecha desde el dibujo
transfiere a un síntoma que nunca vio — y eso es exactamente lo que le faltó al
experimento 01, donde dream abstrajo **ese** caso y no la causa compartida.

**El montaje.** Tres trayectorias reales sobre los primeros bugs de la familia A. El
**mismo corpus** se consolida dos veces: el prompt actual del plugin (`dream.build_prompt`,
no una reconstrucción parecida) contra ese mismo prompt con un bloque `ideate` adelante.
Una sola variable. Después, prueba ciega sobre un bug con **otro síntoma**, con tres
brazos: sin memoria, con el patrón del control, con el patrón ideado. A la sesión ciega se
le inyecta **sólo el patrón**, nunca la ideación: lo que se compara es qué abstracción
transfiere, no cuánto texto se inyecta.

### Lo que dio (2026-08-27, `sonnet`)

Los dos patrones, del mismo corpus:

> **control** — «Varios módulos comparten una función de normalización de claves de texto…
> Al ejecutar los tests con **unittest** aparecen errores de tipo
> `unittest.loader._FailedTest`… El gate se cierra confirmando con **git stash** que sin el
> cambio el test efectivamente rompe.»
>
> **ideado** — «Una corrida de tests muestra un error de carga del framework (module
> fantasma que reemplaza al test real) en lugar de un fallo de aserción; **ese error de
> import enmascara el bug real**, que sólo se ve después de resolverlo y resulta ser una
> función de normalización compartida que no cubre un caso de entrada.»

La ideación que lo produjo llegó a una imagen que el control no tiene:

> «Es una **muñeca rusa**: la primera capa que se abre no es el bug, es el envoltorio que
> lo escondía.»

El control nombra herramientas (`unittest`, `git stash`) — está describiendo *el caso*. El
ideado describe *la forma*: una capa que tapa a otra. Eso es lo que la hipótesis predice.

Y la prueba ciega:

```
brazo         gate    resuelto  turns
sin-memoria   1 → 0   sí        13
control       1 → 0   sí        26
ideado        1 → 0   sí        16
```

**Tres lecturas, y la tercera es la incómoda:**

**1. El ideado le ganó al control**, 16 turns contra 26, con el mismo corpus y la misma
tarea. Es la dirección que predice la hipótesis.

**2. Y los dos perdieron contra no tener memoria** (13). El brazo sin memoria fue el más
rápido de los tres.

**3. Con un brazo por celda esto no distingue nada.** El experimento 01 midió 8, 13 y 10
tool calls en la **misma tarea sin ninguna memoria**: la varianza entre corridas idénticas
cubre de sobra la diferencia entre 13, 16 y 26. Nada de esto es un resultado.

**Un hallazgo que no estaba buscado, y vale más que la comparación:** los dos patrones
abstrajeron un **artefacto del harness**, no el bug del dominio. Lo que las tres
trayectorias comparten de verdad es que el cargador de tests escondió la falla real — y
eso es un patrón cierto y compartido, pero no es la causa que la familia A fue diseñada
para tener en común. Dream abstrae lo que las trayectorias comparten **operativamente**, y
si el andamiaje del experimento aparece en las tres, gana el andamiaje.

**Qué haría falta para decidirlo.** El mismo diseño que M4: tres corridas por brazo,
varios síntomas ciegos, y el umbral fijado antes. El bloque `ideate` vive en
`experimentos/` y **no** en `nightshift/` a propósito — si resulta que sirve, entra al
plugin por el camino normal y no antes.

---

## Cómo leer todo esto

Ninguno de los tres experimentos responde la pregunta del proyecto. Muestran **qué hace la
máquina**, con material real y salidas sin maquillar; el 01 incluso muestra que con esta
cantidad de corridas no se puede concluir nada.

La pregunta —¿recordar cómo se averiguó algo mejora el trabajo de un agente que ya tiene
memoria declarativa?— la responde M4, con tres corridas por celda, tres familias y
umbrales congelados antes de correr una línea. Ver [`../doc/PLAN-M4.md`](../doc/PLAN-M4.md).

---

## preguntar — lo proyectado, resuelto con una persona

**La capacidad que ilustra:** ninguna de las cinco todavía. Es una idea de Matías del
2026-08-27 y esto es la forma más barata de probarla.

**El problema.** `projected_signals` (ADR-004) son síntomas que dream anticipó desde el
dibujo del mecanismo y que **nadie observó**. Se inyectan con la mitad del peso y
anunciados como conjeturas, y ahí termina su vida: no hay ningún camino por el que una
conjetura pase a ser otra cosa. Se acumulan.

**El montaje.** El experimento lee el store en modo sólo lectura, junta las proyecciones
sin resolver y las presenta de a una con su patrón y su diagrama, y con cuatro opciones:

```
1) la vi              La vi pasar. Es una observación, no una conjetura.
2) no puede pasar     Sé por qué no puede ocurrir en este sistema.
3) no la vi todavía   No la vi, pero es plausible: no tengo cómo descartarla.
4) no sé              No tengo forma de saberlo.
```

Son cuatro y no dos a propósito: *"no la vi"* y *"no puede pasar"* son respuestas
distintas, y confundirlas pierde la única información cara de la sesión. La cuarta existe
para que nadie tenga que mentir para seguir.

**Lo que NO hace, que es lo que lo hace honesto:**

- **No escribe en el store.** Lo abre en modo sólo lectura de SQLite —la promesa la
  sostiene la base, no la disciplina de quien lo edite— y el veredicto va a un JSONL
  aparte.
- **No es `verify`.** ADR-002 define verificar como reproducir contra un gate: comando,
  exit code, `run_id`. *"El usuario dijo que sí"* no es eso. Si esto alguna vez entra al
  plugin, entra como un tercer estado —`human_reviewed`— con menos peso que una
  reproducción y más que una conjetura. **Nunca como `procedure`.**
- **No contrasta caminos.** La otra mitad de la idea —varios agentes siguiendo
  alternativas distintas y puliéndose unos contra otros antes de que la vea nadie— no
  está. Cuesta una consolidación por camino, y eso se decide con el veredicto de M4
  delante. Lo que se prueba acá es la **forma de la pregunta**, que es lo barato.

### Lo primero que mostró, sobre el store de este repo

El 2026-08-27 a las 15:27 dream consolidó una candidata sobre el bug de los campos del
payload, y proyectó cuatro síntomas que nadie había visto. Esa misma tarde, midiendo por
otro motivo —una revisión externa del modelo mental—, **dos de los cuatro resultaron
ciertos**:

| Lo que dream proyectó a las 15:27 | Lo que se midió después |
|---|---|
| «El retrieval devuelve coincidencias por forma estructural sin relación con el contenido del trabajo.» | Dos prompts con síntomas distintos devolvían el mismo orden y los mismos scores: el retrieval de lo crudo no miraba el prompt (spec §5.10) |
| «Una revisión manual de un registro reciente muestra la estructura completa y todos los campos de texto en blanco.» | El prompt de dream mostraba seis pasos `(sin resumen)` de una trayectoria de 400 pasos con 177 con contenido (spec §6.1) |

**Y ninguna de las dos se encontró por la proyección.** Estaban escritas, inyectadas y
disponibles, y el trabajo las redescubrió midiendo. Eso es exactamente el agujero que este
experimento tantea: una conjetura que nadie resuelve no es memoria, es una nota.

Para balance, y porque el proyecto reporta lo que no favorece: de otra candidata se
comprobaron dos proyecciones contra el código y **no se sostenían** (`LATER.md`). El
puntaje hasta acá es 2 y 2, sobre seis proyecciones, con n=1 store.
