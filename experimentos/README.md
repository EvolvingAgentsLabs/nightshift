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

```sh
./experimentos/01-mismo-bug-otra-cara.sh          # CONSERVAR=1 para no borrar el trabajo
./experimentos/02-lo-descartado-no-se-pierde.sh
./experimentos/03-cinco-ciclos-sobre-si-mismo.sh
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

## Cómo leer todo esto

Ninguno de los tres experimentos responde la pregunta del proyecto. Muestran **qué hace la
máquina**, con material real y salidas sin maquillar; el 01 incluso muestra que con esta
cantidad de corridas no se puede concluir nada.

La pregunta —¿recordar cómo se averiguó algo mejora el trabajo de un agente que ya tiene
memoria declarativa?— la responde M4, con tres corridas por celda, tres familias y
umbrales congelados antes de correr una línea. Ver [`../doc/PLAN-M4.md`](../doc/PLAN-M4.md).
