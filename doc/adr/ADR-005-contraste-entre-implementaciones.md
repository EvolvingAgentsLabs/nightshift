# ADR-005 — La diferencia entre dos implementaciones es la lección

| Campo | Valor |
|---|---|
| Estado | Aceptada |
| Fecha | 2026-08-27 |
| Decide | Matías |
| Cambia | `mark_superseded`, `dream.consolidate`, la inyección y `why` |

## Contexto

La spec §4.2 promete que nightshift conserva lo contradicho porque *"una alternativa
descartada con su precondición es conocimiento y sin ella es ruido"*. La mitad estaba
construida: `mark_superseded` enlaza la vieja con la nueva y no borra nada.

**La precondición no la calculaba nadie.** El enlace decía *que* una reemplazó a la otra y
nunca qué cambió, qué compró el cambio, ni bajo qué condición la descartada seguía siendo
la correcta. Sin eso, no borrar guarda un cadáver en vez de una lección — y el escenario
que el experimento 02 usa para justificar la capacidad («dentro de tres semanas alguien va
a proponer subir el timeout otra vez») no tenía con qué contestarse.

Y esta sesión produjo el material que lo hace evidente: media docena de cambios donde lo
que se aprendió **no está en ninguna de las dos versiones sino en la diferencia**. El orden
de la matriz del benchmark, el costo en dólares contra el uso en tokens, la familia C con
uno o dos repos, las dos versiones del bloque de ideación. Cada par es "esto se hacía así,
ahora se hace asá, y esto es lo que compró el cambio". nightshift no tenía dónde ponerlo.

## Decisión

Cuando dream encuentra una contradicción registrada, consolida **el contraste**: una
llamada más al modelo con las dos trayectorias, que devuelve qué cambió, qué compró, qué
costó, y `old_valid_when` — el régimen donde la descartada seguía teniendo razón.

El contraste se guarda en la **vieja** (`contrast_json`), porque es la respuesta a "¿por
qué me descartaron?", y se inyecta con la **nueva**, porque quien recibe la ganadora es
quien está por proponer el camino viejo.

El dibujo pasa a ser un **diagrama Mermaid** más dos a cuatro oraciones. Un diagrama es
dibujo y texto a la vez: se lee, se renderiza, y tiene un tope natural de nodos que la
prosa libre no tenía — la ideación anterior devolvía ~2.600 caracteres pidiéndole un
boceto.

## Consecuencias

Corrido sobre una diferencia real de esta sesión —el orden de la matriz del benchmark—
encontró dos cosas que no estaban escritas en ningún lado:

> **qué costó:** «Se paga el costo de conmutación entre brazos una vez por repetición en
> lugar de una vez por brazo, y se pierde la localidad: ningún brazo queda terminado
> temprano.»
>
> **seguía siendo la correcta cuando:** «la corrida está garantizada completa —presupuesto
> por cantidad de celdas y no por tiempo de pared— y el costo de conmutar de brazo
> (recargar un modelo, rehacer un warm-up) domina el costo de una repetición.»

Ninguna de las dos estaba en el commit que hizo el cambio. El commit decía por qué el
orden nuevo es mejor; el contraste dice **qué se pagó** y **cuándo el viejo gana**, que es
lo que hace falta para no deshacer el cambio por accidente dentro de seis meses.

**Lo que cuesta.** Una llamada más al modelo por contradicción. Es raro —requiere una
contradicción registrada, no una opinión— pero no es gratis, y con `dream_max_groups` sin
tope se acumula.

**Un contraste que falla no puede llevarse puesta la supersesión.** El enlace vale por sí
solo, y perderlo sería borrar lo contradicho: exactamente lo que ADR-001 dice que
nightshift no hace y Auto Dream sí. Hay un test que lo fija.

**Y `old_valid_when` es lo más fácil de arruinar.** Un modelo complaciente escribe «cuando
no importa la correctitud», que es una forma elegante de decir «nunca» disfrazada de
matiz. El prompt lo prohíbe explícitamente y pide lista vacía en ese caso. Es la parte que
hay que mirar cuando esto se evalúe: un `old_valid_when` que siempre trae algo es un
`old_valid_when` que no significa nada.

## Alternativas consideradas

**Dejar el contraste como un campo más de la abstracción de la ganadora.** Más barato: sin
llamada extra. Pero la abstracción describe *el patrón del problema*, y el contraste
describe *una decisión entre dos caminos*. Mezclarlos hace que la ganadora hable de dos
cosas a la vez y que la descartada siga sin tener respuesta propia — `why` sobre la vieja
seguiría sin decir nada.

**Derivar el contraste del diff de git en vez de las trayectorias.** El diff dice qué
líneas cambiaron; la trayectoria dice qué se intentó y qué falló. `old_valid_when` sale de
lo segundo. Además ataría nightshift a git, que hoy sólo usa para el fingerprint y el
commit base.

**Pedir el contraste sin ideación.** Se probó en el mismo formato que el resto: el bloque
de ideación va adelante cuando la estrategia es `ideate`, para que el contraste salga del
mismo dibujo que la abstracción y no de una segunda lectura de los pasos.
