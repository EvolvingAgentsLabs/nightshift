# Experimentos

Experimentos que se corren solos y muestran qué hace nightshift que la memoria
declarativa nativa no hace. Están escritos para reproducirse, no para convencer: varios
dieron resultados que **no favorecen al plugin**, y están reportados igual.

Todos corren sobre copias desechables y stores desechables. **Ninguno toca tu store ni
suma al conteo del gate de M1.**

| | Qué muestra | Cuesta |
|---|---|---|
| [01](01-mismo-bug-otra-cara.sh) | El mismo bug con otra cara: qué transfiere, la traza o el patrón | 6 sesiones de agente + 1 dream |
| [02](02-lo-descartado-no-se-pierde.sh) | Lo que se descartó sobrevive enlazado, con su precondición | 1 dream |
| [03](03-cinco-ciclos-sobre-si-mismo.sh) | Cinco ciclos del plugin sobre sus propios problemas | 5 sesiones + 5 dreams |
| [04](04-ideacion-visual.sh) | Un bloque `ideate` antes de abstraer: ¿el dibujo transfiere mejor que la prosa? | 6 sesiones + 2 consolidaciones |
| [05](05-enganche-por-parafrasis.py) | ¿El enganche por síntoma sobrevive a que lo digas con otras palabras? | nada: compara frases |
| [07](07-idear-contra-no-idear.py) | ¿Idear compra transferencia a un síntoma retenido, y no idear no? | 1 llamada al modelo |
| [08](08-el-techo-del-oraculo.py) | El techo: con la respuesta esperada escrita a mano, ¿funciona todo? ¿falla el código o el prompt? | nada: no llama al modelo |
| [09](09-lectura-en-frio.py) | ¿Las conjeturas son profecías o horóscopos? Especificidad y sensibilidad | nada: no llama al modelo |
| [10](10-abstencion.py) | ¿Dream se abstiene cuando no hay patrón, o siempre encuentra uno? | 2 llamadas al modelo por repetición |
| [11](11-la-profecia-tiene-notario.py) | ¿Cuánta de la evidencia del proyecto sobrevive a que la revise un script? | nada: lee el store y corre git |
| [12](12-sensibilidad.py) | ¿Llega la conjetura el día que hace falta? Necesita un retenido escrito por una persona | nada, y hoy está BLOCKED |
| [preguntar](preguntar.py) | Lo proyectado, presentado como opciones para que una persona lo resuelva | nada: lee el store y pregunta |

```sh
./experimentos/01-mismo-bug-otra-cara.sh          # CONSERVAR=1 para no borrar el trabajo
./experimentos/02-lo-descartado-no-se-pierde.sh
./experimentos/03-cinco-ciclos-sobre-si-mismo.sh
./experimentos/04-ideacion-visual.sh
python3 experimentos/05-enganche-por-parafrasis.py --alternativas
python3 experimentos/07-idear-contra-no-idear.py
python3 experimentos/08-el-techo-del-oraculo.py
python3 experimentos/09-lectura-en-frio.py
python3 experimentos/10-abstencion.py --repeticiones 3
python3 experimentos/11-la-profecia-tiene-notario.py
python3 experimentos/12-sensibilidad.py
python3 experimentos/preguntar.py --dry-run       # sin --dry-run, pregunta
```

De todos, el **05** es el único que cambió el plugin: encontró que el enganche por
síntoma se caía a cero en cuanto el usuario parafraseaba, y de ahí salió la enmienda 0.3.6
de la spec. Los demás miden y no tocan nada.

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

## 05 — El enganche contra la paráfrasis

**La capacidad que ilustra:** ninguna nueva. Prueba si las que ya están declaradas
funcionan cuando el usuario habla como habla una persona.

**De dónde sale.** La spec §5.10 se escribió midiendo el ranking contra el store real, y
lo que midió fue **discriminación**: que dos prompts con síntomas distintos no devuelvan el
mismo orden. Quedó verificado. Lo que nadie midió es la otra mitad, y es la del README:
*«cuando abrís la sesión siguiente y describís lo que te está pasando, te devuelve lo que
ya se probó»*. Nadie describe un síntoma con las palabras exactas con las que un modelo lo
escribió la noche anterior.

**El montaje.** Las frases reales de la única candidata del store de este repo
(`fff6af83`), contra tres corpus de prompts: la frase textual (control positivo), catorce
paráfrasis de cómo lo diría una persona, y seis prompts de otro planeta (control negativo).

### Lo que dio

| | antes | después |
|---|---|---|
| paráfrasis que enganchan (corpus del experimento) | 3 de 14 | **9 de 14** |
| paráfrasis que enganchan (store real, extremo a extremo) | 1 de 6 | **4 de 6** |
| control negativo | 0 de 6 | 0 de 6 |

**El enganche por síntoma se caía a cero en cuanto se parafraseaba**, que es la única
forma en que alguien lo escribe. La causa: `_enganche` pedía dos palabras de contenido en
común, y les cobraba el mismo peaje a dos clases de texto que no se parecen — una oración
que el modelo destiló, donde no hay relleno, y un volcado de error, que es casi todo
andamiaje del harness.

De acá salió la **enmienda 0.3.6**: dos pisos en vez de uno. Con la medición que dice por
qué el de lo crudo **no** baja — bajarlo produce un falso positivo sobre los errores reales
de este store, y dejarlo en 2 no produce ninguno, que es el caso que §5.10 ya había
documentado con `Exit code 1`.

**Y un segundo hallazgo, del propio arreglo.** Bajar el piso de lo destilado introdujo un
falso positivo: «el deploy falla con un certificado SSL vencido» enganchaba con «esa etapa
no falla ante contenido ausente» por la palabra `falla` y nada más. Medido sobre nueve
prompts ajenos, los enganches de una sola palabra se reparten limpio: los verdaderos los
carga un sustantivo del dominio (`vacio`, `texto`, `registro`, `paso`) y el único falso lo
carga un predicado (`falla`). De ahí `_PREDICADOS_DE_FALLO`: dicen **que** algo se rompió,
no **qué**, y no pueden sostener un enganche solas.

**Lo que este experimento no demuestra:** que nightshift sirva. Que la memoria aparezca no
es que ayude — eso lo decide M4. Y las paráfrasis las escribió quien mide, así que son
material de trabajo: están en texto plano dentro del archivo para que se discutan de a una.
El único lado que no depende de ese criterio es el control negativo.

**Dos de seis siguen sin enganchar**, y no se disimulan: «dos resúmenes de tareas
diferentes me salieron prácticamente iguales» y «las métricas dicen que está todo bien pero
es mentira». Ninguna comparte una sola palabra de contenido con el patrón que las
describiría. Eso es un problema de sinónimo, no de morfología: `difflib` y el emparejado por
prefijo se probaron y no compran nada — están en el archivo, con su número. Resolverlo
necesita embeddings, que chocan con ADR-003 (stdlib, sin red). Queda en `LATER.md`.

---

## 07 — Idear contra no idear, con un conjunto retenido

**La capacidad que ilustra:** ninguna. Es el **control de ADR-004**, la apuesta central del
proyecto: *el dibujo de un mecanismo es invariante entre síntomas de un modo que la prosa
no lo es.*

**El montaje.** El mismo corpus (`cbbd7ff0`) consolidado de las dos maneras —el prompt del
plugin con y sin el bloque `ideate`— medido contra un conjunto **retenido** que ninguno de
los dos brazos vio: tres síntomas que una persona confirmó después con `nightshift
resolve`, escritos con paráfrasis a mano. Más un control negativo de tres prompts ajenos.

**Cómo se evita que sea circular.** Contar proyecciones por brazo sería trampa: `observed`
no puede producir ninguna. Preguntarle al brazo ideado por sus propias proyecciones sería
peor: las escribió él. Por eso el retenido y las paráfrasis humanas.

### Lo que dio (2026-08-28, medido por el camino real)

```
síntoma retenido (paráfrasis humana)   control   ideado
panel de salud con denominador cero    no        no
ensayo verde contra store vacio        SI        SI
linter con lista vacia                 no        SI
engancha                               1 de 3    2 de 3

control negativo (3 prompts ajenos):   0         1
```

**Idear enganchó un síntoma retenido más, y lo pagó con un prompt ajeno.** Más superficie
engancha más de las dos cosas: mientras el control negativo no dé 0, la transferencia extra
no se puede separar de la indiscriminación, y la hipótesis pide justamente esa separación.
No refuta ADR-004 — la deja **sin sostener**, que es distinto. Para cerrarla hace falta
volumen, que es lo mismo que le falta a todo lo demás de este repo.

**Los números cambiaron el 2026-08-28, y hacia arriba.** Antes de esa fecha este
experimento decía *control 2, ideado 2* — empate. El instrumento estaba mal: armaba un
bolsón de frases `signals + pattern + decisive_signal` y la cadena real nunca matchea
contra `pattern`. Lo encontró el `08`. Corregido, el control pierde un enganche que la
máquina nunca produjo. **El veredicto no cambió**: sigue sin sostener ADR-004, ahora por el
control negativo y no por un empate.

---

## 08 — El techo del oráculo: ¿falla el código o falla el prompt?

**La capacidad que ilustra:** ninguna. Es un **diagnóstico** del `FAIL` de H17, no una
medición del plugin.

**El problema.** H17 falla y el `FAIL` no dice dónde arreglar. Dos culpables posibles:
la cadena no transporta ni la abstracción perfecta (se arregla **código**), o la
transporta y el modelo no escribió esa abstracción (se arregla el **prompt**).

**El montaje.** Un tercer brazo, el **oráculo**: la abstracción esperada, escrita a mano,
metida por el camino real —`promote_to_candidate` sobre un store desechable,
`retrieve.candidates`, `retrieve.render`— contra los mismos tres síntomas retenidos y el
mismo control negativo. No mide enganche con un helper: mide si el bloque se **inyecta**.

**Qué NO es, y va antes que el resultado.** El oráculo se escribió con el conjunto
retenido a la vista: gana por construcción. **No es evidencia, no sostiene ADR-004 y no
convierte H17 en `PASS`** — H17 mide brazos que no vieron el retenido. Es un **techo**:
sirve por lo que descarta. Lo que no es trivial, y por eso el experimento dice algo, es
llegar a 3 de 3 **sin** enganchar el control negativo.

### Lo que dio (2026-08-28)

```
brazo                                  retenidos    control negativo
control (observed)                     1 de 3        0 de 3
ideado (real, cbbd7ff0)                2 de 3        1 de 3
ORÁCULO (techo, conoce el retenido)    3 de 3        0 de 3
ORÁCULO, pero diciendo `linter`        3 de 3        1 de 3
```

**1. La cadena puede.** Con la abstracción esperada, los tres retenidos enganchan por
`signal_match` y `projected_match`, el ranking los pone primeros y `render` los inyecta,
sin tocar una línea de `retrieve.py`. Lo que le falta a H17 no es código de retrieval.

**2. La colisión la carga una sola palabra.** El mismo oráculo, cambiando `linter` por
`chequeo` en una proyección, pasa de 1 falso positivo a 0. El matcher tiene resolución de
sobra; lo que no tiene es un prompt que le pida nombrar el mecanismo y no la herramienta.

**3. Y un defecto en el instrumento de H17, que es lo que más valió.**
H17 y el 07 medían el enganche contra `signals + pattern + decisive_signal`. El camino real
—`retrieve.candidates`— **nunca matchea contra `pattern`**, y sí matchea contra
`valid_when`, que el instrumento no miraba. El único enganche del brazo de control al
retenido "el chequeo pasa porque su patrón no encontró ningún archivo" venía **sólo** de
`pattern`: en la cadena real ese enganche no ocurre.

**Corregido el 2026-08-28**, y de la única forma que no se vuelve a romper: no hay bolsón
de frases en ningún lado. El 07, el 08 y H17 miden con `camino_real.medir` —candidata
montada, `candidates`, `render`— y la única definición de "engancha" es la del plugin. La
corrección mueve el marcador del control de 2 a 1, o sea a favor del plugin, y por eso el
veredicto se endureció al mismo tiempo: H17 ahora exige además que el control negativo dé
0. Sigue en `FAIL`.

---

## 09 — ¿Profecía u horóscopo? El control de lectura en frío

**De dónde sale.** El proyecto trata sus proyecciones confirmadas como su mejor evidencia.
Pero dicen cosas como *"un panel informa cobertura perfecta cuando el denominador es cero"*
— bugs que cualquiera que sepa programar predice sin haber visto la trayectoria. Un
horoscopista acierta por lo mismo. Nadie había probado que fueran **específicas**.

**El montaje.** Cada una de las 23 conjeturas del store se monta **sola** —una candidata
con esa conjetura y nada más, así el enganche es atribuible a ella— contra dos corpus
ajenos: 10 prompts de otro dominio (frontend, ML, mobile, firmware, cobros) y 8 del mismo
género con otro mecanismo (test flaky, coverage, mock que no se resetea). Ese segundo es el
control difícil. Y como comparación, los 3 síntomas retenidos que una persona confirmó.

### Lo que dio (2026-08-28), y da vuelta la pregunta

```
                        con lo retenido   con lo ajeno
conjeturas de cbbd7ff0  4 de 15  (27%)    5 de 90  (6%)
las 23 del store         —                20 de 414 (5%)
```

**1. No son horóscopos.** Enganchan 5 veces más con el síntoma que anticiparon que con
cualquier otra cosa, y el control difícil no las tumba. Una sola excepción: la del `linter`,
que engancha por el sustantivo de la herramienta — la misma colisión que ya había aparecido
en el 07.

**2. Y el problema real es el opuesto, que nadie estaba buscando.** La sensibilidad es
**27%**. Ninguna conjetura engancha más de 1 de los 3 síntomas retenidos, y la primera que
una persona confirmó —el panel con el denominador en cero— **no engancha ninguno**, ni
siquiera la paráfrasis del síntoma que ella misma anticipó.

No sobran conjeturas que se enciendan con todo: **faltan conjeturas que se enciendan con lo
suyo.** Es una profecía que nadie puede consultar, y una memoria que no llega el día que
hacía falta no es memoria. El riesgo que este experimento venía a descartar no era el riesgo
que el proyecto tenía.

---

## 10 — ¿Dream se abstiene cuando no hay patrón?

**Por qué es la pregunta más barata y más peligrosa del proyecto.** Las familias A, C y D
del benchmark tienen la causa compartida **plantada a mano**: A es un normalizador roto que
rompe diez módulos, C es la misma etapa que se traga la excepción en dos repos. Medir ahí
si dream encuentra el patrón es medir si encuentra algo que alguien puso para que
encuentre. Nadie midió nunca lo contrario. El código sabe recibir `{"pattern": null}` y los
tests lo cubren **con un modelo de mentira**: lo probado era la cañería, no la conducta.

**El montaje.** Cuatro grupos en `bench/fixtures/familia-e/grupos.json`. Dos sin mecanismo
compartido —`sin-01`, dominios obviamente distintos; `sin-02`, el difícil, tres bugs que
sólo comparten género— y dos con mecanismo compartido, que son el control obligatorio: un
modelo que contesta `null` siempre pasaría la primera mitad con nota perfecta.

### Lo que dio (2026-08-28)

```
                        se abstuvo donde NO había    abstrajo donde SÍ había
antes de la regla       0 de 3                       3 de 3
después de la regla     3 de 3                       3 de 3
```

**No sabía decir que no.** Con tres trabajos sin absolutamente nada en común —un margen de
CSS, un índice faltante en una base, una coma de más en un JSON— encontró un patrón las tres
veces. Y lo que encontró era cierto y vacío: *"el fallo se reporta en la coordenada donde el
estado inválido se consume"*, que describe casi cualquier bug.

**La palanca era el prompt.** Se le agregó a `dream.PROMPT` una regla dura: antes de escribir
un patrón, exigirse poder señalar **el paso concreto de cada trayectoria** donde el mismo
mecanismo actúa; si para una sola hay que argumentar, no hay patrón. Pasó a 3 de 3 **sin
perder** ninguna de las abstracciones correctas, que es la mitad que hacía falta cuidar.

**Y la generalización, que es la parte interesante.** La regla se escribió mirando
`sin-01`, así que ese 3 de 3 no dice que generalice. Contra los grupos que no la vieron:

```
sin-02  (negativo ambiguo)  0 de 3 abstenciones
sin-03  (negativo limpio)   3 de 3 abstenciones
con-02                      3 de 3 abstracciones
```

`sin-02` **falló, y el que estaba mal era el fixture.** Sus tres trayectorias eran un zip
que se corrompe en Windows (modo texto que traduce saltos de línea), un botón deshabilitado
por un validador async, y un cron que corre dos veces en el cambio de horario. Dos de esas
tres **sí comparten mecanismo**: un valor reinterpretado por una convención en un borde. El
modelo encontró ese par y estiró el patrón para cubrir al tercero — que es exactamente la
conducta que la regla prohíbe, pero medida contra un negativo que no era negativo.

`sin-03` se construyó con la regla explícita —**ningún subconjunto comparte mecanismo**: un
validador async, un listener que nunca se da de baja, y un comparador con los argumentos al
revés— y ahí sí, 3 de 3.

**Las dos cosas quedan escritas y `sin-02` se conserva**, con su defecto anotado en el
fixture: midió algo real, que el modelo estira un patrón para cubrir al miembro que sobra.
Es una hipótesis nueva y no está comprobada — hace falta un negativo con un par adentro,
construido a propósito, y no queda claro todavía qué debería contestar.

De acá salió la **familia E** del pre-registro (`bench/PREREG.md` §3-E), abierta por decisión
de Matías el 2026-08-28, con sus dos umbrales en `TODO(Matias)`.

---

## 11 — La profecía tiene fecha, ¿y el arreglo tiene commit?

**De dónde sale.** La regla 2 de `CLAUDE.md`: *si no se puede automatizar, no es un gate, es
una opinión*. La mejor evidencia del proyecto —las cinco proyecciones de `cbbd7ff0`
resueltas una por una— vive en un campo de texto libre: `resolved_by = "sesión 2026-08-28,
PR 54"`. Una persona lo lee y entiende; un gate no.

**El montaje.** Git como notario. Para cada conjetura resuelta: ¿el registro nombra un
objeto verificable? ¿existe en la historia? ¿es posterior a la trayectoria que la produjo y
sigue siendo ancestro de `HEAD`?

### Lo que dio (2026-08-28)

```
notarizadas por git: 4 de 8
```

Las cuatro de `cbbd7ff0` pasan las tres preguntas: la conjetura es del 2026-08-27T15:25Z, el
arreglo es el merge de PR #54 del mismo día a las 21:03, y sigue vivo en la historia. **Eso
es la afirmación que el proyecto quería poder hacer, y ahora la hace un script.**

Las otras cuatro no, y el motivo es incómodo: **no es que la evidencia sea peor, es que el
autor escribió el nombre de un archivo de notas en vez de un número de PR.** Un accidente de
redacción está decidiendo qué parte del proyecto es auditable.

---

## 12 — ¿Llega la conjetura el día que hace falta?

**Estado: `BLOCKED`, y es lo correcto.** El `09` midió que la sensibilidad de las conjeturas
es 27%. Se le agregaron dos reglas a `dream.PROMPT` que apuntan ahí, y **no se pueden medir
contra el retenido de `cbbd7ff0`**: ese conjunto se gastó diagnosticando y el prompt se
escribió mirándolo.

Lo que falta no es código: es que una persona que **sólo vio las conjeturas** escriba con sus
palabras cómo describiría cada síntoma. El protocolo y el archivo a llenar están en
[`retenido/`](retenido/). Si las paráfrasis las escribe quien mide, lo único que se mide es
cuánto se parece a sí mismo.

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

El 2026-08-27 a las 15:25:34Z dream consolidó una candidata sobre el bug de los campos del
payload, y proyectó cuatro síntomas que nadie había visto. Esa misma tarde, midiendo por
otro motivo —una revisión externa del modelo mental—, **dos de los cuatro resultaron
ciertos**:

| Lo que dream proyectó a las 15:25 | Lo que se midió después |
|---|---|
| «El retrieval devuelve coincidencias por forma estructural sin relación con el contenido del trabajo.» | Dos prompts con síntomas distintos devolvían el mismo orden y los mismos scores: el retrieval de lo crudo no miraba el prompt (spec §5.10) |
| «Una revisión manual de un registro reciente muestra la estructura completa y todos los campos de texto en blanco.» | El prompt de dream mostraba seis pasos `(sin resumen)` de una trayectoria de 400 pasos con 177 con contenido (spec §6.1) |

**Y ninguna de las dos se encontró por la proyección.** Estaban escritas, inyectadas y
disponibles, y el trabajo las redescubrió midiendo. Eso es exactamente el agujero que este
experimento tantea: una conjetura que nadie resuelve no es memoria, es una nota.

Para balance, y porque el proyecto reporta lo que no favorece: de las otras dos, una se
comprobó contra el código y **no se sostenía** (`LATER.md`), y la otra sigue abierta.

**El puntaje completo, y es el único que se puede abrir y contar:**

| | |
|---|---|
| proyecciones | **4**, todas de la candidata `fff6af83` |
| confirmadas | 2 — el retrieval por forma, y el registro con los campos en blanco |
| refutadas | 1 — los contadores de cobertura |
| abiertas | 1 — «las memorias consolidadas de trabajos distintos resultan casi idénticas entre sí» |
| stores | 1 |

**Sobre la que sigue abierta, hay un dato y no alcanza para cerrarla.** El 2026-08-27, con
la captura ya arreglada, un `dream --dry-run` sobre el store real produjo una segunda
candidata de trabajo genuinamente distinto al de la primera:

| candidata | patrón |
|---|---|
| `fff6af83` (`general`) | «Una cadena de captura conserva la estructura de cada paso pero pierde su contenido…» |
| `cbbd7ff0` (`implement_feature`) | «El trabajo se verifica adentro del artefacto y se ejecuta afuera: el veredicto verde lo emite un gate que lee el módulo afectado como archivo…» |

No se parecen en nada, que es lo contrario de lo que la proyección anticipa. **Y aun así se
queda abierta**, por tres motivos que conviene no saltear: es n=2, salió de un dry-run que
no escribió nada, y sobre todo la conjetura nació **mientras la captura estaba vacía** — si
todos los pasos llegan sin contenido, dos consolidaciones cualesquiera *sí* saldrían casi
idénticas. Lo más probable es que fuera cierta bajo las condiciones que la produjeron y
haya dejado de serlo al arreglarse la captura, y eso no es "refutada": es una conjetura
cuya precondición cambió. Distinguir las dos cosas es exactamente el trabajo que `verify`
(M5) va a tener que hacer solo.

```sh
sqlite3 ~/.nightshift/trajectories.sqlite3 \
  "select projected_signals_json from trajectories where status='candidate';"
```

**Acá decía "2 y 2, sobre seis proyecciones", y era falso.** Las dos cuentas de más no
existen: la segunda refutación que se reportaba no está en el store, ni en los logs, ni en
ninguna salida guardada de dream. La corrección, con lo que probablemente pasó, está en
`LATER.md`. Que el número inflado haya sobrevivido en el único lugar donde el proyecto
publica su puntaje es el mismo modo de falla que este repo lleva tres secciones
documentando: **una explicación plausible anotada como hallazgo.**

Una anécdota con numerador, y el numerador tiene que ser el de verdad.
