# ADR-004 — Dream idea el mecanismo y proyecta hacia adelante

| Campo | Valor |
|---|---|
| Estado | Aceptada |
| Fecha | 2026-08-27 |
| Decide | Matías |
| Cambia | `dream.consolidate` (fase 1), el retrieval de `UserPromptSubmit`, y el esquema |

## Contexto

Dream fase 1 mira para atrás: agrupa trayectorias cerradas y abstrae el patrón que
comparten. Eso deja dos agujeros que se midieron, no que se supusieron.

**El patrón sale fiel y poco portable.** El experimento 01 lo mostró con una trayectoria:
dream abstrae *ese* caso, no la causa compartida. La familia A tiene diez bugs con una
causa justamente porque el patrón tiene que salir de varios; con pocos, describe el
síntoma que vio.

**Y la memoria sólo sirve cuando el síntoma se repite.** El retrieval rankea por tipo de
tarea y repo. Un bug con la misma causa y otra cara no engancha con nada: la memoria
existe, es correcta, y no aparece. Ése es el caso que el proyecto dice que resuelve.

El experimento 04 probó una salida, propuesta por Matías: **idear antes de abstraer.**
Describir el mecanismo como un dibujo —una escena, un diagrama, dos cuadros de animación—
y abstraer desde ahí. La hipótesis es falsable: *el dibujo de un mecanismo es invariante
entre síntomas de un modo que la prosa no lo es.*

Con el mismo corpus, el patrón ideado describió la forma («una capa que tapa a otra»)
donde el control describió el caso (nombró `unittest`, `git stash`). En la prueba ciega el
ideado le ganó al control, 16 turns contra 26. **Y los dos perdieron contra no tener
memoria, 13.** Con un brazo por celda eso no distingue nada: la varianza medida entre
corridas idénticas ya es más grande que esa diferencia.

## La ideación busca la visualización canónica, no cualquier dibujo

La primera versión del bloque pedía "describí el mecanismo como un dibujo". Es la mitad de
la idea. Lo que la completa —y lo que Matías planteó— es que hay explicaciones que sólo se
entienden cuando alguien las dibuja **bien**, y el dibujo correcto no agrega información:
saca la que sobra.

La DFT no es una sumatoria con exponenciales: es enrollar la señal alrededor de un círculo
a cada velocidad y mirar dónde queda el centro de masa. La convolución es dar vuelta una,
deslizarla, y anotar el solapamiento. Una integral es una aplicación que acumula área. La
transformada Z es una superficie donde los polos son postes y los ceros clavan al piso, y
la respuesta en frecuencia es la altura del terreno cuando caminás el círculo unidad.

El bloque pide eso: **la imagen más corta que vuelve obvio el invariante**, y de paso la
pregunta que la DFT enseña a hacer — *qué magnitud se conserva y cuál se pierde*.

Medido sobre el mismo corpus, con el mismo modelo, cambiando sólo el bloque:

| | primera versión | con la visualización canónica |
|---|---|---|
| el dibujo | «una capa que tapa a otra» | «un import relativo es un vector en coordenadas locales; cargarlo suelto mueve el origen y el término desaparece» |
| la magnitud perdida | no la busca | **N: cuántas aserciones se ejecutaron de verdad.** «Verde no significa nada se rompió, significa nada de lo que llegó a correr se rompió» |
| proyecciones | 4, genéricas | 5, y una encontró un hueco real en este repo |
| tokens de salida | 1.715 | 4.866 |

La última fila es el costo y no se disimula: **casi el triple de salida por grupo.** Un
dibujo mejor sale más caro, y con `dream_max_groups` sin tope una noche larga lo
multiplica.

**Lo que encontró.** De la proyección *«un test recién agregado no se ejecuta nunca y
nadie lo advierte, porque el total no se compara contra ningún valor esperado»* salió
`tests/test_suite.py`: la suite se audita a sí misma y falla si un archivo de tests deja
de aportar. Ningún archivo aportaba cero ese día — que no es lo mismo que estar protegido.
Es el mismo modo de falla que ya costó dos milestones acá: la captura guardaba estructura
vacía y no fallaba nunca.

Un mecanismo que produce conjeturas y una de ellas cierra un agujero real es la primera
evidencia a favor de esto que no vino de compararse contra sí mismo.

**Segunda vez, el 2026-08-27, y esta vez el ciclo cerró entero sobre el propio repo.**
Dream consolidó una sesión de desarrollo y proyectó cinco síntomas que nadie había
observado; la sesión siguiente los fue a mirar contra el código. Dos estaban —el panel de
salud del ensayo decía "la máquina corre entera" con cero celdas y salía 0, por el camino
normal de una corrida sin ninguna repetición completa—, una tercera estaba en forma
latente, una se refutó y la quinta es una decisión abierta que no cierra un agente. El
detalle, con el veredicto de cada una y sin redondear la cuenta, está en `LATER.md`.

Sigue sin ser evidencia de que **idear** produzca mejores proyecciones que no idear.

**Y el 2026-08-28 se corrió el control, con el resultado en contra.**
`experimentos/07-idear-contra-no-idear.py`, sobre `cbbd7ff0` y contra un conjunto
**retenido** —tres síntomas que una persona confirmó después, con paráfrasis escritas a
mano— que ninguno de los dos brazos vio:

| | transferencia (3 retenidos) | control negativo (3 ajenos) |
|---|---|---|
| `observed` | **2 de 3** | 0 |
| `ideate` | **2 de 3** | **1** |

Empate en transferencia, y una colisión de más para el brazo ideado: *«el linter se queja
de un import sin usar»* enganchó con la proyección sobre un linter cuya lista quedó vacía,
por compartir la palabra `linter`. Mismo sustantivo, problema distinto — es más débil que
un falso positivo limpio, y el control no la hizo.

**Sobre n=1 corpus, idear no compró transferencia y su superficie extra costó una
colisión.** Eso no refuta la hipótesis: la deja **sin sostener**, que es distinto. Lo que
sí queda medido es que la evidencia a favor sigue siendo la de arriba —un agujero real
tapado— y no una ganancia en el mecanismo que el ADR postula.

La comparación se diseñó para no ser circular: contar proyecciones por brazo sería trampa
(`observed` no puede producir ninguna) y preguntarle al brazo ideado por sus propias
proyecciones sería peor. Por eso el conjunto retenido y las paráfrasis humanas.

## Decisión

Dream idea el mecanismo, abstrae desde el dibujo, y **proyecta**: desde el mecanismo,
anticipa en qué otras formas se va a manifestar. Esos síntomas proyectados entran al
retrieval, así que la memoria puede engancharse con un problema **antes de que su síntoma
se haya visto una vez**.

`consolidation_strategy` en la config elegía: `observed` era el comportamiento anterior,
`ideate` el nuevo, y el default.

**Actualizado el 2026-08-27 (enmienda 0.3.7 de la spec): la clave ya no existe.**
`consolidate` idea siempre. El motivo es que `observed` **no puede** producir
`projected_signals`, así que la única capacidad que engancha con un problema antes de que
su síntoma se haya visto una vez quedaba detrás de un default. El brazo de control
sobrevive como `build_prompt(..., ideate=False)`, alcanzable sólo desde
`experimentos/ideate.py`: sin control no se puede volver a medir la diferencia, pero que
el control exista no lo vuelve una opción del producto.

Se acepta con la evidencia que hay, que es de n=1 y no alcanza para afirmar que funciona.
Lo que la sostiene no es el resultado del experimento 04 sino el agujero que tapa: sin
esto, la capacidad que el proyecto dice tener —transferir a un síntoma distinto— no tiene
ningún mecanismo detrás, sólo la esperanza de que el ranking estructural alcance.

## Consecuencias

Lo que esto cuesta, dicho antes y no después.

**Un síntoma proyectado es una conjetura que nadie observó.** Es la primera vez que
nightshift inyecta algo que no le pasó a nadie. Un patrón crudo es débil pero ocurrió; una
proyección puede ser simplemente falsa, y suena igual de bien.

La frontera se defiende en código, en los cuatro lugares donde puede borrarse:

- **Se guarda aparte.** `projected_signals_json`, nunca dentro de `signals`. Una
  proyección que se cuela entre las observadas deja de ser conjetura y pasa a ser dato.
- **Pesa la mitad.** `W_PROJECTED_MATCH` es exactamente `W_SIGNAL_MATCH / 2`, y hay un
  test que lo fija. No es calibración: una la vio alguien y la otra la anticipó un modelo.
- **Se anuncia.** La inyección dice «síntomas anticipados por dream — NINGUNO fue
  observado, son conjeturas», y `why` las lista aparte de las señales.
- **Pasa los mismos gates.** Ideación y proyecciones son texto de modelo y se persisten:
  una fuga en cualquiera de las dos voltea la consolidación entera, igual que en el patrón.

**Y cambia qué es el brazo S1 de M4.** Una corrida con `observed` y otra con `ideate` no
son comparables. Por eso la estrategia es una **constante del experimento** —está en
PREREG §2 y hay que congelarla como cualquier otra— y no una preferencia del usuario.
Desde la enmienda 0.3.7 la constante está fijada por el código en `ideate`: si M4 llegara
a correr, ése es el valor que hay que escribir en el pre-registro, y congelarlo en
`observed` exigiría volver a abrir el interruptor a propósito.

**Y una tercera consecuencia, medida después (enmienda 0.3.7).** Proyectar no alcanza si
lo proyectado llega último: sobre el store real, la única fila que enganchaba por síntoma
proyectado quedaba tercera de tres, detrás de dos trayectorias en verde que no compartían
una palabra con el prompt. Un enganche con el prompt ahora ordena antes que cualquier
puntaje sin enganche. La mitad del peso de `W_PROJECTED_MATCH` **no cambió** —lo proyectado
sigue valiendo la mitad de lo observado y el test lo fija— porque esa mitad decide entre
dos filas que las dos enganchan, no si la conjetura llega o no llega.

## Alternativas consideradas

**Dejarlo en `experimentos/` hasta después de M4.** Es lo que recomendé y lo que el
pre-registro pide: cambiar el consolidador con n=1 justo antes de medir es exactamente lo
que existe para impedir. Matías decidió lo contrario, con el argumento de que sin este
mecanismo M4 mide una versión del sistema que no tiene cómo cumplir su propia tesis.
Queda escrito así para que dentro de seis meses se pueda evaluar la decisión y no sólo el
resultado.

**Proyectar sin idear.** Pedirle al modelo "¿de qué otras formas se manifiesta esto?"
sobre el patrón en prosa. Es más barato y probablemente peor: la prosa ya perdió el
mecanismo, así que la proyección se hace sobre el síntoma. El dibujo es lo que retiene la
estructura, y es la parte de la hipótesis que se puede falsar.

**Que lo proyectado pese igual que lo observado.** Haría el mecanismo más efectivo y a
nightshift menos honesto. La distinción entre lo que ocurrió y lo que se supone es la
única razón por la que esto es memoria.

## Cómo se sabe si estuvo bien

M4 con la estrategia congelada. Y una familia que hoy no existe: síntomas ciegos —bugs con
la misma causa y otra cara— con tres corridas por brazo y umbral fijado antes. El
experimento 04 es el boceto de esa familia, no su resultado.

La señal de que estuvo **mal** es específica y hay que buscarla: inyecciones donde el
único motivo es `projected_match` y el agente sigue una pista que nadie observó. Si eso
pasa seguido, el peso está mal o el mecanismo no sirve.
