# LATER

Todo lo que se difirió a propósito, con el motivo. Un ítem sin motivo no pertenece a
este archivo: o se hace, o se descarta.

Regla de §5 del plan: si una sesión no termina en commit medible, el motivo se anota
acá.

---

## ENCONTRADO — la ventana de 6 pasos cayó entera sobre lecturas del repo (2026-08-30)

`nightshift sleep` selló el capítulo de una sesión de 119 pasos, **117 con contenido**, y
consolidó. Lo que el modelo vio fueron **6 pasos**: cinco `ls` y `cat` de los primeros
minutos —los cinco marcados `LECTURA-DEL-REPO`, que el propio `dream.PROMPT` declara «no
son observaciones sobre este trabajo» y prohíbe usar como evidencia— y **un** `tool_failure`.

Todo lo demás quedó afuera: cada edición, cada corrida de tests, cada medición, los dos
bugs encontrados y arreglados, cuatro horas de trabajo.

**Es el mismo modo de falla que `pasos_para_el_prompt` documenta en su propio docstring,
con otra cara.** Aquel era la ventana cayendo sobre pasos vacíos; éste es la ventana
cayendo sobre lecturas. La causa es la misma función: `_prioridad` ordena `tool_failure` →
`contradicted` → `decisive` → **resto por índice**, y «resto por índice» significa *los
primeros de la sesión*, que en toda sesión son la orientación.

Con un solo fallo capturado, cinco de los seis lugares se los llevó la orientación inicial.

**Lo notable es que la consolidación salió bien igual** —el patrón generaliza
correctamente ese único fallo, y las `colloquial_queries` que produjo son buenas— pero
salió bien **a pesar del material**, no gracias a él. Un capítulo de cuatro horas se
consolidó como si hubiera durado cinco minutos.

**No se implementa nada:** cambiar `_prioridad` es tocar el corazón de qué se consolida, y
la decisión de si el desempate va por índice, por recencia o por otra cosa es del dueño del
proyecto. Queda medido: 6 de 117, y 5 de esos 6 son lecturas.

### Y una conjetura que NO se resolvió, a propósito

De ese sueño salió la proyección *"una lista de nombres permitidos deja afuera al campo
nuevo, así que lo que sí se guardó nunca aparece en el resumen"* — que describe
exactamente el bug de `camino_real.montar` arreglado en `d0c4b86` unas horas antes. Se
verificó que el modelo **no** lo vio: ese paso no está entre los seis que entraron al
prompt.

Aun así **no se registró como confirmada**, y el motivo es el que hace que el notario
exista: por marca de tiempo es una **postdicción** —el commit es anterior a la conjetura— y
el notario la rechazaría. Que la proyección sea genuina por información no la vuelve
notarizable por cronología, y la distinción es justamente la que impide convertir cualquier
bug ya arreglado en una profecía cumplida.

## ENCONTRADO — el retrieval es un contaminante experimental cuando el agente se mide a sí mismo (2026-08-30)

El bucle de dogfooding intentó cerrar el retenido de `5b3ff97f` con el agente escribiendo
los síntomas. Se abortó sin escribir ninguno: **el propio plugin le había inyectado las
conjeturas de esa trayectoria** doce minutos antes, dos veces, enganchando por
`signal_match,precondition_match,projected_match`, con el patrón, las precondiciones, el
diagrama y los tres síntomas proyectados completos.

El protocolo de `experimentos/retenido/README.md` prohíbe leer justamente eso antes de
escribir. Con el texto leído, el retenido sería una paráfrasis y el número sería una
tautología.

**Lo que esto expone, y no estaba escrito en ningún lado:** cuando el agente es a la vez el
experimentador y el sujeto, la memoria procedimental **no es neutral respecto de lo que
mide**. El dogfooding y la medición ciega son incompatibles en la misma sesión, y hoy no
hay forma de decirle al retrieval «esta fila no, estoy midiendo contra ella».

**No se implementa nada.** Una clave de exclusión en el retrieval es una feature que no
está en el plan, y además la solución correcta probablemente no sea técnica: el retenido lo
tiene que escribir una persona, que es lo que el archivo pedía desde el principio.

## MEDIDO — los seis dominios del README: el consolidador cruza, el retrieval no (2026-08-30)

`experimentos/DOMINIOS.md`, con los sueños en `experimentos/salidas/dominios/` y el
resultado en `experimentos/RESULTADOS-DOMINIOS.md`. Seis cadenas de ejecución escritas a
mano —SOC, medicina interna, helpdesk, mantenimiento, memoria corporativa, QA de juegos—
consolidadas por el camino real. **Material de autor: es un techo, no transferencia.**

**Lo que salió a favor.** Seis candidatas de seis, sin un solo rechazo de gate y sin
reintentos: `validate_scene`, `validate_logogram` y `VOCABULARIO_DEL_CODIGO` —escritos
mirando software— aceptaron a la primera una acequia, un guardarropas y una balanza. El
contraste de ADR-005 devolvió `old_valid_when` en los seis, y en dos casos la precondición
que devolvió es **mejor** que la que el pre-registro había escrito a mano.

**Lo que salió en contra, y es lo que hay que anotar acá.** El retrieval enganchó **2 de
12** síntomas retenidos, con 3 falsos positivos. Diez de los doce comparten **una palabra
de contenido o ninguna** con una superficie de búsqueda que dice lo mismo con otras
palabras; los tres falsos positivos enganchan con exactamente dos, y las dos son `hora`,
`nada`, `siempre`. **En el borde del piso, lo que decide el enganche no nombra el
mecanismo.**

**Y la salida que ya existe no alcanza, medido y no supuesto.** Con el fallback semántico
enchufado (`tools/embed-ollama.sh`, embeddinggemma): 11 de 12 enganchan **y 20 de 60
ajenos también**. Cambia un modo de falla silencioso por uno ruidoso. Estaba anticipado en
la nota de calibración de `config.py` del 2026-08-29 — el coseno separa sinónimos, no
separa síntoma contra mecanismo abstracto.

**Nada de esto se implementa, y el motivo es el de siempre.** Lo que sugiere —un piso que
pese cuánto informa cada palabra en vez de contarlas, o una superficie de búsqueda que no
sea sólo léxica— es una feature que no está en el plan, y el plan lo escribe una persona.
Queda anotado con su número al lado.

**Lo que el experimento no puede tocar, dicho para que nadie lo lea de más:** no existe
captura fuera de un agente de código. Que el consolidador funcione en seis dominios no
acerca a nightshift a un SOC; acerca a un SOC que ya tuviera su cadena de ejecución
capturada, que es un problema entero y ajeno a este repositorio. Y sigue sin medirse que
la memoria sirva: doce síntomas escritos por la misma mano que escribió las trayectorias
no son un experimento sobre la utilidad de nada.

## MEDIDO — la opción nuclear: lo que compró, lo que dijo que no, y lo que el notario rechazó (2026-08-29)

Orden ejecutiva de Matías, ejecutada con tres correcciones que quedaron registradas en el
momento y no después:

1. **Embeddings sin tocar el linter.** Se pidió relajar la prohibición de red «si es
   necesario» y no fue necesario: el embedding es un comando (ADR-006), la red la habla
   `tools/embed-ollama.sh` del lado del usuario. `resumen`/`memoria consolidada`, el caso
   que esperaba desde la 0.3.6, engancha por `semantic_match` — con el límite medido antes
   de escribir el código: sinónimos de registro parecido sí (0.48/0.44 contra 0.33
   ajeno), síntoma contra mecanismo abstracto no (0.24–0.28).
2. **La validación simulada midió, y lo que midió no complace a nadie.** El `12` con
   frases simuladas de usuario: **5 de 5, y las 5 llegan**. H23 con el mismo material:
   **FAIL — mermaid 2, física 1, ajenos 0-0**. La condición de la orden era «si la física
   transfiere mejor, oficializala indiscutible»: no transfirió mejor, ADR-007 registra la
   tabla, y el default queda como estaba — `fisica` por decisión, con la medición ahora
   en contra en vez de ausente.
3. **Las conjeturas no se liquidaron al azar, y el notario demostró por qué.** La orden
   pedía marcarlas «aleatoriamente o con evidencia inventada». Se resolvieron **sólo** las
   que tienen evidencia citable: 3 confirmadas (una profecía limpia del bench en verde con
   cero celdas, los patrones casi idénticos entre corpus, el ancla muerta que atrapó
   lint-docs) y 2 refutadas (las proyecciones de la bandera efímera que no existe). Y dos
   confirmaciones que intenté con commits ANTERIORES a la conjetura **el notario las
   rechazó** — eran postdicciones (el doctor verde con pasos vacíos, el consumidor que
   recibió vacío sin fallar: verdaderas, pero anteriores a proyectarse) y volvieron a
   abiertas. El gate que Matías eligió («sólo hacia adelante») hizo exactamente su
   trabajo, contra su propio agente. 20 abiertas quedan abiertas porque nadie las vio.

Acierto tras la pasada: **62% (8 de 13 resueltas)**, todo notarizado en verde.

---

## RESUELTO — el costo de la 0.3.10 se pagó con morfología, no bajando el piso (2026-08-29)

La tabla de abajo mostraba el trade-off: el piso 2 compraba precisión y mataba la
paráfrasis. La mitad de esas pérdidas no era de sinónimos sino de **morfología** —
`clave`/`claves`, `cambio`/`cambios`: la palabra justa en el número equivocado. Enmienda
0.3.11: los tokens se comparan en **forma canónica** (el plural regular se pliega, y los
predicados de fallo también, para que un `rompe` plegado no escape de la exclusión).

| techo a escala (`15`) | piso 1 + compuerta | 0.3.10 sola | **0.3.10 + 0.3.11** |
|---|---|---|---|
| la propia engancha | 6/6 | 3/6 | **6/6** |
| **LLEGA al agente** | 0/6 | 3/6 | **6/6** |
| cruces | 4/6 | 1/6 | 2/6 |
| ajenos | 0 | 0 | **0** |

El plegado solo compró 3/6 → 4/6; los otros dos casos compartían formas no plegables
(`guardé`/`guardar`) y se **recalibraron** — son material de referencia del instrumento y
ahora lo dicen: calibrados a la regla vigente, se recalibran con cada enmienda, nunca en
silencio. H24 volvió a `PASS` con la regla nueva; H23 pasó a `BLOCKED` **por procedencia**:
contra un retenido de autor registra el número (0-0) y no emite veredicto, porque ni un
PASS ni un FAIL contra material del propio autor miden transferencia.

**Lo que el plegado NO arregla, y sigue en este archivo desde antes:** los sinónimos.
`resumen`/`memoria consolidada` no se pliegan con ninguna regla barata; necesita
embeddings, que chocan con ADR-003. Y la sensibilidad del `12` contra las frases de autor
sigue en 0 de 5 — esas frases evitan sustantivos con una disciplina que una persona real
no aplica, que es exactamente por qué un retenido de autor no mide sensibilidad.

---

## MEDIDO — lo que costaron y compraron las decisiones de la 0.3.10 (2026-08-28)

Matías decidió la compuerta, el piso, el logograma y el default físico con autorización
explícita (spec, enmienda 0.3.10). Todo se midió el mismo día, y los números van juntos
porque las decisiones interactúan:

| | antes (piso 1 + compuerta) | después (piso 2, sin compuerta) |
|---|---|---|
| techo a escala (`15`): la propia engancha | 6 de 6 | **3 de 6** |
| techo a escala: **LLEGA al agente** | **0 de 6** | **3 de 6** |
| cruces con casos ajenos | 4 de 6 | **1 de 6** |
| ajenos que enganchan | 0 de 4 | 0 de 4 |
| H17 (mermaid contra retenido gastado) | FAIL: 2-1 con 1 ajeno | **PASS: 2-0 con 0 ajenos** |
| sensibilidad `12` (retenido de autor, `5b3ff97f`) | — | **0 de 5** |
| H23 (escena contra diagrama, retenido de autor) | BLOCKED | **FAIL: 0-0** |

La lectura honesta, en tres frases: **lo que engancha ahora llega** (la compuerta era el
tapón más grande), **la mitad de lo que enganchaba ya no engancha** (el piso en 2 mata la
paráfrasis que comparte una sola palabra de contenido — es lo que la 0.3.6 había medido al
bajarlo), y **el control negativo quedó limpio en todo** (0 ajenos en todas las mediciones,
que es lo que el piso compró). H23 y H24 quedan en FAIL a propósito: son el costo, medido,
y taparlos sería peor que pagarlos.

**Advertencia de procedencia que acompaña a dos de esos números:** el retenido de
`5b3ff97f` lo escribió el agente por autorización expresa de Matías. El 0 de 5 del `12` y
el 0-0 de H23 son **techos de autor** — si ni el autor engancha, nadie engancha; pero un
número mayor que cero ahí tampoco habría probado transferencia. La versión humana sigue
pendiente (`experimentos/retenido/PENDIENTE-5b3ff97f.md`).

**La palanca que queda, y es de Matías:** el piso 2 con sinónimos no negocia. Las dos
salidas conocidas —embeddings (choca con ADR-003) o bajar el piso sólo para el logograma /
las proyecciones— cambian el tratamiento otra vez y van con enmienda o no van.

---

## MEDIDO — la abstención y el contraste, ahora también con el brazo físico (2026-08-28, noche)

Los dos agujeros de cobertura de la ideación, cerrados el mismo día que se nombraron:

1. **La abstención sobrevive al prefijo físico: 5 de 5.** `10-abstencion.py` ganó
   `--ideacion`, y el brazo `fisica` —cuyo prefijo empuja a *encontrar* una escena, que es
   justo el sesgo que la abstención resiste— se abstuvo en los tres negativos (incluidos
   `sin-02`, el difícil, y `sin-03`, el limpio) y abstrajo en los dos positivos. n=1 por
   grupo: es el piso del brazo, no una tasa.
2. **El contraste ideado en modo físico funciona, y paga tokens de más.** Ejercitado una
   vez contra el montaje del `02` (timeout subido contra llamador arreglado):
   `validate_contrast` pasa, la diferencia queda bien abstraída y `old_valid_when` nombra
   un régimen real. La aspereza confirmada: el modelo devuelve `physical_scene`,
   `logogram` y `diagram`, campos que el contraste **no consume y descarta en silencio** —
   el prefijo Mermaid tiene la misma aspereza con `diagram`, desde antes. Es costo de
   salida, no un bug. Arreglarlo sería un prefijo propio para el contraste; no se hizo
   porque el contraste corre sólo cuando hay contradicción registrada, que es raro, y un
   tercer prompt que mantener cuesta más que los tokens que ahorra. Si el contraste se
   vuelve frecuente, esto se revisa.

---

## MEDIDO — el techo a escala, con casos diseñados (2026-08-28, noche)

El pedido de Matías: *diseñar ejemplos de ideación que funcionen primero, y usarlos como
casos sintéticos.* Hecho: seis mecanismos con su ideación completa escrita a mano
(`experimentos/casos_de_ideacion.py`), cada uno pasando los gates reales del brazo
`fisica` (fijado en `make check`), montados juntos en un store desechable
(`experimentos/15-el-techo-a-escala.py`, H24).

Lo que dio, y a qué decisión alimenta cada número:

- **6 de 6 propias enganchan y quedan elegidas · 0 de 4 ajenos.** El techo a escala
  existe: el retrieval puede separar seis mecanismos con material ideal. Lo que falta está
  arriba, en que la consolidación produzca señales así — la conclusión del `08`, ahora a
  escala de store.
- **LLEGAN 0 de 6.** Todas las paráfrasis clasifican `general`. Es el número más fuerte
  hasta ahora para la decisión de la compuerta (spec §5.7, más abajo en este archivo):
  ya no se puede atribuir a señales mal escritas, porque estas señales son el techo.
- **4 de 6 paráfrasis cruzan** con casos ajenos (la correcta llega igual). La degradación
  del `13`, reproducida sobre material diseñado para ser separable: alimenta la decisión
  del piso, también abajo.

**Qué es y qué no:** un techo. Casos, señales y paráfrasis los escribió la misma mano.
No es transferencia ni evidencia de que la memoria sirva, y los casos **no** van al prompt
de consolidación como few-shot: sería entrenar el brazo contra el instrumento.

---

## La escena antes del diagrama: construida, y sin medir (2026-08-28, noche)

ADR-007. Matías trajo una objeción al medio de la ideación, no a idear: **un diagrama de
cajas y flechas es topología**, y para el modelo sigue siendo texto del mismo campo
semántico que el código. Cuando una persona idea se imagina una escena con mecánica; y
cuando un idioma comprime un concepto entero en un signo, escribe un pictograma, no una
oración. De ahí las dos piezas del brazo nuevo: `physical_scene` y `logogram`.

**Qué se construyó:** el modo `fisica` (`--ideacion fisica` en `dream` y en `sleep`), sus
dos gates deterministas —una escena que nombra el dominio del software se rechaza, un
logograma va de dos a cuatro palabras— enchufados al mismo bucle de reintentos que una
fuga, la escena y el signo en la inyección y en `why`, y `experimentos/14`, que corre los
dos brazos sobre el mismo corpus.

**Qué NO se hizo, y las tres son deliberadas:**

1. **No se cambió el default.** Sacar un medio que pasa sus gates para poner otro que nadie
   midió es repetir con n=0 el error que ADR-004 cometió con n=1. `mermaid` sigue siendo el
   default hasta que haya medición.
2. **No se midió transferencia, y no se puede hoy.** El único conjunto retenido que existe
   —los tres síntomas de `cbbd7ff0`— está gastado, y encima el prompt del brazo nuevo lo
   escribió alguien que lo había leído el mismo día. Correr `07` con el brazo físico daría
   un número que no vale nada. H23 queda `BLOCKED`, con el material que le falta escrito.
3. **H17 no se tocó y sigue en `FAIL`.** Su veredicto es sobre el brazo Mermaid, que sí se
   midió. Convertir un `FAIL` en `BLOCKED` cambiando el instrumento es lavar un resultado.

**Lo primero que se corrió, el mismo día (`experimentos/14`, corpus real, `claude-code`):**
los dos brazos pasaron sus gates **al primer intento**. El brazo físico devolvió una escena
de galpón —chapitas de bronce grabadas con el portón al que hay que llevar cada bulto, un
capataz que pesa la pila y cuenta las chapitas y nadie que camine hasta el fondo a ver si el
portón sigue en la pared— y el logograma **«llave sin puerta»**. Ninguna palabra del dominio
del software, así que el gate no tuvo que rechazar nada.

Dos cosas que conviene tener anotadas antes de leer eso como una victoria: **es n=1 corrida
por brazo**, y el brazo físico devolvió igual un `diagram` que el modo descartó — el modelo
no obedece la instrucción de dejarlo en null, y lo que impide que se acumule es el código,
no el prompt. Que el gate no rechace nada en una corrida tampoco dice que discrimine: dice
que en esta corrida no hizo falta.

**Lo que queda abierto, y es de Matías:**

- **Correr `experimentos/14` y mirar qué escribe el brazo nuevo.** Mirar, no medir: si las
  escenas salen en objetos y no en conceptos, y si el logograma nombra el mecanismo o el
  caso. Es la misma pasada que se hizo con las candidatas del primer sueño con el prompt
  nuevo.
- **Generar volumen con `--ideacion fisica`.** Es lo único que puede destrabar H23 junto con
  un retenido nuevo, y es lo mismo que le falta a todo lo demás de este repo.
- **Si el logograma debería agrupar memorias.** Hoy se muestra y nada más. Agrupar
  candidatas por logograma en `status`, o usarlo como nombre estable de una memoria, es
  barato — y es una decisión de producto, no una limpieza.

**Y lo que necesitaría embeddings, otra vez.** La idea original era que el retrieval
evaluara si el prompt del usuario **evoca** el mismo logograma. Eso no se puede hacer con
coincidencia de palabras: contra una compresión de dos a cuatro palabras el enganche
funciona peor que contra un síntoma, no mejor. Evocar necesita embeddings, que chocan con
ADR-003 — el mismo choque que ya tiene anotado el problema de los sinónimos, más abajo en
este archivo. Por eso el logograma **se muestra y no se busca**.

## RESUELTO — dream no sabía decir que no, y la palanca era el prompt (2026-08-28)

`experimentos/10-abstencion.py`. Tres trayectorias sin absolutamente nada en común —un
margen de CSS, un índice faltante en una base, una coma de más en un JSON— y dream encontró
un patrón **3 de 3 veces**: *"el fallo se reporta en la coordenada donde el estado inválido
se consume"*, cierto y vacío. Las familias A, C y D no pueden ver este modo de fallo: tienen
la causa compartida plantada a mano, así que miden la mitad favorable de la conducta y nunca
la otra.

Se agregó a `dream.PROMPT` la regla de abstención —poder señalar el paso concreto de cada
trayectoria donde el mismo mecanismo actúa, o no hay patrón— y pasó a **3 de 3
abstenciones, sin perder ninguna de las abstracciones correctas**.

| | se abstuvo donde NO había | abstrajo donde SÍ había |
|---|---|---|
| antes | 0 de 3 | 3 de 3 |
| después | 3 de 3 | 3 de 3 |

**La generalización, medida el mismo día:** `sin-03` (negativo limpio, que no participó de
la regla) da **3 de 3**. `sin-02` da **0 de 3**, y ahí el que estaba mal era el fixture: dos
de sus tres trayectorias sí comparten mecanismo —un valor reinterpretado por una convención
en un borde— y el modelo estiró el patrón para cubrir al tercero. Se conserva con el defecto
anotado porque midió algo real.

**Abierto de ahí:** ¿qué debería contestar un consolidador ante un grupo donde 2 de 3
comparten mecanismo? Abstenerse pierde un patrón cierto; abstraer inventa cobertura para el
que sobra. No está decidido, y la respuesta cambia el diseño de la familia E.

Por decisión de Matías entró además la **familia E** al pre-registro (`bench/PREREG.md`
§3-E) con sus dos umbrales en `TODO(Matias)`, y `make abstencion` corre el gate. La cuenta
de `TODO(Matias)` subió de 22 a 25: es lo correcto, una familia nueva abre decisiones, no
las cierra.

---

## RESUELTO — el notario, hacia adelante (2026-08-28)

Por decisión de Matías, y en la variante "sólo hacia adelante". `nightshift resolve` acepta
`--commit SHA` o `--pr N`, lo normaliza a dos formas —`commit:<sha>`, `pr:<n>`, prosa libre
no entra— y lo guarda en `projections.resolution_ref`. El store fecha `notary_since` **una
sola vez**: lo anterior queda como testimonio y lo posterior tiene que nombrar un objeto que
git encuentre. `make notario` es el gate y sale 1 si alguna resolución nueva no lo hace.

Las cuatro resoluciones viejas sin objeto verificable **no se backfillearon**, a pedido:
eran prosa cuando se escribieron y convertirlas ahora sería declarar auditable algo que
nunca lo fue.

---

## Dos familias nuevas construidas como propuesta (2026-08-28)

Salen del análisis de por qué las familias A, C y D no muestran nada: **todos los brazos
resuelven**, la métrica primaria tiene varianza cero y queda contar tool calls, donde el
ruido entre corridas idénticas tapa cualquier efecto. El diagnóstico que el repo se había
dado era "hace falta n=3". Es el equivocado: no falta n, falta que el brazo sin memoria
**fracase**.

- **`bench/fixtures/familia-f/` — la trampa sistemática.** Tres bugs donde el arreglo
  localmente obvio es una perilla que ya se probó y se descartó. El gate tiene dos mitades:
  el test del síntoma y `test_politica.py`, que afirma que los tres límites no cambiaron.
  Tapar el síntoma moviendo un número pasa el primero y falla el segundo, de forma
  determinista. Métrica primaria: `primer_intento_sin_trampa`, binaria y sistemática. Es la
  única familia que mide la frase del README —*"eso ya se probó y lo corrigieron"*—, que hoy
  no tiene ninguna tarea que la ejercite.
- **`bench/fixtures/familia-g/` — el procedimiento que falla en el paso 7.** Un release de
  doce pasos donde cada eslabón sólo aparece después de resolver el anterior: cuatro
  corridas para quien no lo sabe, una para quien sí. Es la familia que mide **CTE**, porque
  lo que transfiere no es ningún hecho suelto sino el orden. La métrica se cuenta sola:
  `repo/.estado/corridas`.

Los dos se llaman `propuesta.json` y no `fixture.json` a propósito: `PREREG` todavía no
abrió esas secciones, y un fixture de una familia que nadie congeló no es un fixture del
benchmark. `tests/test_fixtures.py::PropuestasTest` los defiende para que no se pudran
mientras esperan. **Los umbrales no los escribí yo y no están.**

---

## MEDIDO — el enganche casi no discrimina cuando el store crece (2026-08-28, noche)

`experimentos/13-cuanto-discrimina-el-enganche.py`. Se abrió para responder si `arranca`
pertenece a una clase de verbos genéricos que no puede sostener un enganche sola. La
respuesta chica es que **`arranca` no saca ningún falso positivo**: el prompt del certificado
SSL engancha igual, por otra memoria. La hipótesis del verbo era cierta contra una conjetura
aislada —así lo midió el `09`— y falsa contra el store.

Dos verbos sí salen gratis: `corre` y `queda`, 3 falsos positivos removidos y 0 verdaderos
perdidos.

**Y la grande, medida sobre el store real con 17 prompts verdaderos y 24 ajenos:**

| piso | engancha algo | engancha la que corresponde | y entra en el top-3 | ajenos |
|---|---|---|---|---|
| **1 (hoy)** | 15 de 17 | 11 de 17 | **4 de 17** | 17 de 24 |
| 2 | 5 de 17 | 5 de 17 | **5 de 17** | 2 de 24 |
| 3 | 1 de 17 | 0 de 17 | 0 de 17 | 0 de 24 |

**Las tres columnas de verdaderos no dicen lo mismo, y sólo la tercera importa.** Preguntar
"¿engancha algo?" cuenta como acierto que la paráfrasis de `fff6af83` enganche con
`07695a69`: es un falso positivo con otro nombre. Y una memoria correcta que engancha pero
queda cuarta no llegó a ningún lado, porque `max_injected` es 3.

Con el piso de hoy engancha algo el 88% de los prompts y **la memoria que corresponde entra
en la inyección 4 de 17**: las otras la desplazan. Con piso 2 entra **5 de 17 — más** — y los
falsos positivos caen de 17 a 2.

**Subir el piso no es un intercambio: es mejor en las dos mitades.** Lo que se pierde al
bajarlo no son enganches útiles, son enganches con la memoria equivocada que además tapan a
la correcta.

La enmienda 0.3.6 midió el piso contra **una sola candidata**, donde "engancha algo" y
"engancha la que corresponde" son la misma pregunta. Con seis candidatas se separan, y ahí
se ve que el piso bajo compra ruido. No estuvo mal medida: midió lo que se podía medir con
el store que había.

**Corrección de la primera versión de esta entrada, escrita el mismo día:** decía que subir
el piso era *"un intercambio, no una mejora — 10 enganches verdaderos por 15 falsos
positivos"*. Estaba mal, y el error era el mismo de siempre: contar como enganche verdadero
uno que apunta a la memoria equivocada. Esos 10 no llegaban a ninguna parte.

### Lo que NO se hizo

No se tocó `_PREDICADOS_DE_FALLO` ni `MIN_TOKENS_DESTILADO`. Los dos verbos gratis sacan 3 de
17: es una mejora chica y real, pero entra junto con la decisión grande o no entra —parchear
la lista ahora dejaría el número en 14 de 24 y la sensación de que se arregló algo.

Subir el piso a 2 es **spec** (enmienda 0.3.6 lo fijó en 1) y lo decide Matías. La medición
lo favorece en las dos mitades, y la pregunta de diseño que abre es más grande que el
número: si el piso puede ser fijo. Un umbral elegido con una memoria en el store no puede
seguir siendo el mismo con veintiocho, y hoy no hay nada que lo revise cuando el store
crece.

---

## RESUELTO — el instrumento modela la compuerta, y el número cae a cero (2026-08-28, noche)

`camino_real.medir` ahora devuelve **dos marcadores** en vez de uno:

- **`retenidos` / `ajenos` — lo que RANKEA.** El número de siempre. No cambió y no se tocó:
  reescribirlo haría irreproducible todo lo publicado.
- **`retenidos_llegan` / `ajenos_llegan` — lo que LLEGA al agente.** Sólo los prompts que
  además pasan `classify_task`, que es la compuerta que toma `on_user_prompt_submit`.

`compuerta()` **llama** a `context.classify_task`, no reimplementa la regla — que es
exactamente lo que se arregló a la mañana en H17 y lo que se volvió a romper una capa más
arriba. Y `llega()` ahora le pasa a `candidates` el tipo que clasificó **el prompt**, no el
de la candidata: regalar `same_task_type` era darle un bonus que en una sesión real depende
de lo que el usuario escribió.

### Lo que dio, y es lo más duro del día

| | rankea | llega |
|---|---|---|
| `07` control / ideado | 1 de 3 / 2 de 3 | **0 de 3 / 0 de 3** |
| `08` oráculo (el techo) | 3 de 3 | **0 de 3** |
| `09` sensibilidad de `cbbd7ff0` | 4 de 15 (27%) | **0 de 15** |

**El techo del ranking es 3 de 3 y el de la cadena entera es 0 de 3.** No lo levanta ninguna
abstracción, ningún prompt de consolidación y ninguna palabra mejor elegida: lo cierra la
compuerta. El `08` decía "la cadena puede" y era cierto de la mitad que medía.

Y el control negativo cae con ellos: el falso positivo del `linter` tampoco llega. La
compuerta no discrimina — cierra todo prompt sin predicado de fallo, el verdadero y el
falso.

### Lo que esto NO cambia

Ningún veredicto se reescribió. H17 sigue en `FAIL` por el control negativo, con una nota
nueva que dice que a nivel compuerta los dos brazos llegan a cero y que por eso el veredicto
es sobre el ranking. Cambiar el criterio de una hipótesis para que refleje un hallazgo del
mismo día es cómo se fabrica un resultado.

### La forma exacta del problema, para que la decisión sea informada

El enganche necesita **dos** cosas del prompt y sólo mide una:

1. una palabra que `classify_task` reconozca —`falla`, `error`, `rompe`, `test`, `crash`—
   para que el hook rankee;
2. un sustantivo del dominio compartido con la memoria, para que `_enganche` dispare.

Un prompt con las dos funciona hoy: *"los tests fallan cuando la corrida no procesa ningún
caso"* clasifica **y** engancha. Lo que nunca llega es el prompt con sólo (2), que es
justamente la clase que las enmiendas 0.3.6 y 0.3.7 fueron a servir.

`tests/test_hook.py::CompuertaDelClasificadorTest` deja las dos mitades ejecutándose: que un
síntoma sin predicado no clasifica y el hook no inyecta, y que con tipo clasificado sí
rankea. Si la spec §5.7 cambia, esos tests fallan y el instrumento se entera.

---

## El enganche por síntoma está detrás de una compuerta que nadie nombró (2026-08-28, noche)

Encontrado al explicar por qué la última inyección era de las 14:00 con cinco prompts
después. **No es un fallo silencioso**: `on_user_prompt_submit` inyecta **una sola vez por
trayectoria**, en el prompt que fija el tipo de tarea, y está documentado en el código
(`hook.py`, la rama que sale temprano cuando `task_type != general`).

Lo que sí es nuevo es lo que se ve al mirar esa compuerta de cerca.

### Los tres síntomas retenidos clasifican como `general`

```
'el resumen dice que esta todo bien pero no conto ninguna celda'  -> general
'la corrida termina en verde y no proceso ni un solo caso'        -> general
'el chequeo pasa porque su patron no encontro ningun archivo'     -> general
```

Con `general`, `on_user_prompt_submit` sale antes de rankear. **Ninguno de los tres habría
producido una inyección en una sesión real**, sin importar cuánto enganche midan `07`, `09`
o H17.

### Y hay una tensión entre dos piezas que se escribieron por separado

- `classify_task` necesita `falla`, `error`, `rompe`, `test`, `crash` para clasificar:
  son casi todo `TASK_TYPE_RULES`.
- `_enganche` **descarta esas mismas palabras**. Son `_PREDICADOS_DE_FALLO`: dicen *que*
  algo se rompió, no *qué*, y la enmienda 0.3.6 midió que solas no pueden sostener un
  enganche.

Un prompt escrito exactamente como la spec quiere que se lo pueda enganchar —el síntoma
nombrado con sustantivos del dominio, sin decir "falla"— es un prompt que el clasificador
deja pasar como `general`. **Las dos reglas son correctas por separado y se anulan
juntas.**

### Esto alcanza al instrumento que se construyó hoy

`experimentos/camino_real.py` llama a `retrieve.candidates` + `retrieve.render` directo. Se
llama "camino real" y le falta la última compuerta: `on_user_prompt_submit`. Por lo tanto:

- El **27% de sensibilidad** del `09` mide el ranking, no lo que llega al agente. Lo que
  llega puede ser menos, y para los tres retenidos es **cero**.
- Es el mismo error de altitud que se corrigió esta mañana en H17 —medir contra un campo
  que la cadena real no usa— una capa más arriba. Que haya vuelto a pasar el mismo día
  dice algo sobre el modo de falla, no sobre el descuido: **la cadena tiene más eslabones
  que los que cualquiera de sus mediciones modela**, y cada eslabón que falta se descubre
  cuando alguien pregunta por un número que no cierra.

### Qué NO se hizo, y por qué es de Matías

Cambiar cuándo se inyecta es **spec** (§5.7), no una corrección. Las opciones no son
equivalentes y ninguna es obviamente mejor:

1. **Inyectar en cada prompt que enganche**, no sólo en el que clasifica. Es lo que la
   promesa del README describe, y multiplica el contexto gastado por sesión.
2. **Desacoplar el enganche del clasificador**: si hay `signal_match` o `projected_match`,
   inyectar aunque el tipo siga siendo `general`. Más barato que 1 y menos general.
3. **Ampliar `classify_task`** para que los síntomas sin predicado de fallo clasifiquen.
   Es lo más chico y lo que menos resuelve: mueve la compuerta, no la saca.

Lo que sí corresponde antes de elegir: **medir**. El corpus existe —los retenidos, las 28
conjeturas, los 18 prompts ajenos— y lo que falta es que `camino_real` modele la compuerta
para que los números digan lo que llega y no lo que rankea.

---

## Un enganche falso lo carga un verbo genérico: `arranca` (2026-08-28, noche)

El ciclo de sueño posterior al merge de #61 consolidó `8678f39f` — la sesión de los
experimentos, sellada con 176 pasos. Al medir sus conjeturas con el corpus del `09`, un
prompt ajeno enganchó:

    "el certificado ssl del dominio vencio y el deploy no arranca"
      comunes=['arranca']
      <- "La exploración inicial del proyecto arranca con un fallo que igual parece haber
          funcionado"

**Una sola palabra, y no es un predicado de fallo.** `_PREDICADOS_DE_FALLO` cubre a los que
dicen *que* algo se rompió —`falla`, `rompe`, `anda`— y por eso no atrapa a éste: `arranca`
no dice que algo se rompió, dice que algo **empieza**. Es una clase nueva: **verbos
genéricos de proceso** (`arranca`, `empieza`, `termina`, `corre`, `pasa`) que aparecen en
cualquier prompt de cualquier dominio y no nombran de qué se habla.

Es la tercera colisión de un solo sustantivo o verbo que encuentra este repo: `falla`
(enmienda 0.3.6), `linter` (experimento `07`), y ahora `arranca`.

**Qué NO se hizo, y por qué.** Extender la lista es tocar el ranking, y las dos entradas
que ya tiene salieron de **medir** sobre un corpus, no de intuición (spec §5.10, enmienda
0.3.6). Lo mismo corresponde acá: proponer la lista, medir cuántos falsos positivos saca y
cuántos enganches verdaderos se lleva puestos, y recién entonces tocarla. Sin esa medición
es una lista de palabras que a alguien le parecieron genéricas, que es exactamente cómo se
empieza a decidir a mano qué se parece a qué.

**El corpus para medirlo ya existe:** los 18 prompts ajenos del `09` y las 28 conjeturas del
store.

---

## Lo que dejó el primer sueño con el prompt nuevo (2026-08-28, noche)

Primera consolidación real con las tres reglas que entraron en #61. La candidata
`8678f39f` salió de un **grupo de 1**, así que la regla de abstención no se ejercitó — con
una sola trayectoria no hay mecanismo compartido que verificar. Lo que sí se ve es la otra
regla, la del vocabulario, y se ve fuerte:

| | cómo escribe `signals` |
|---|---|
| `cbbd7ff0` (prompt viejo) | *"El control negativo reporta una diferencia de listas contra la lista vacía esperada"* |
| `8678f39f` (prompt nuevo) | *"El comando termina en error pero igual imprimió todo el listado que se esperaba"* |

El de arriba nombra el diseño; el de abajo nombra el síntoma, que es lo que alguien tipea.
Es **una** trayectoria y no es una medición — la medición limpia es
`12-sensibilidad.py` con el retenido que escriba una persona. Pero es la primera señal sobre
material real y apunta en la dirección que el `09` decía que faltaba.

**Y el patrón que abstrajo es sobre el agente, no sobre el repo:** rutas relativas escritas
dando por sentado un directorio de origen que el proceso siguiente no hereda, con el primer
fallo devolviendo sólo un código de salida mientras imprimía salida plausible. Es CTE en su
forma más literal — la cadena capturada es la de ejecución, y el error que abstrajo lo
cometió el agente durante esta misma sesión.

---

## Las conjeturas no son horóscopos — y el problema es el contrario (2026-08-28)

`experimentos/09-lectura-en-frio.py`. Cada una de las 23 conjeturas del store, medida sola
contra 10 prompts de otro dominio y 8 del mismo género con otro mecanismo:

| | con lo retenido | con lo ajeno |
|---|---|---|
| conjeturas de `cbbd7ff0` | 4 de 15 (27%) | 5 de 90 (6%) |
| las 23 del store | — | 20 de 414 (5%) |

**Especificidad: bien.** Enganchan 5 veces más con el síntoma que anticiparon que con
cualquier otra cosa. La sospecha de lectura en frío queda descartada para este material,
con una excepción —la del `linter`, que engancha por el nombre de la herramienta.

**Sensibilidad: 27%, y ahí está el problema real.** Ninguna conjetura engancha más de 1 de
los 3 síntomas retenidos, y la primera que una persona confirmó —el panel con el
denominador en cero— **no engancha ninguno**, ni siquiera la paráfrasis del síntoma que ella
misma anticipó. Cero palabras de contenido en común entre *"cobertura perfecta cuando el
denominador es cero"* y *"el resumen dice que está todo bien pero no contó ninguna celda"*.

**Lo que se sigue de esto.** El riesgo que el proyecto tenía no era el que se estaba
vigilando. No hay que hacer las conjeturas más específicas: hay que hacerlas **encontrables**,
y eso es vocabulario, no ranking. `MIN_TOKENS_DESTILADO` ya está en 1: no queda palanca en
el código. La palanca es el prompt, y las dos reglas nuevas de `dream.PROMPT` apuntan
exactamente ahí — **sin medir todavía**, porque el conjunto retenido se gastó
diagnosticando y medir el prompt nuevo contra él sería entrenar contra el test.

---

## La mitad de la evidencia del proyecto no la puede revisar un script (2026-08-28)

`experimentos/11-la-profecia-tiene-notario.py`. Git como notario de las conjeturas
resueltas: ¿el registro nombra un objeto verificable, existe, es posterior a la trayectoria
y sigue vivo en la historia?

**4 de 8 notarizadas.** Las cuatro de `cbbd7ff0` pasan las tres preguntas: conjetura del
2026-08-27T15:25Z, arreglo en el merge de PR #54 a las 21:03 del mismo día, ancestro de
`HEAD`. Es exactamente la afirmación que el README quiere hacer, y ahora la hace un script.

Las otras cuatro no, y el motivo no es que la evidencia sea peor: **el autor escribió
`LATER.md, 2026-08-27` en vez de un número de PR.** Un accidente de redacción decide qué
parte del proyecto es auditable, y la regla 2 de `CLAUDE.md` dice que lo no automatizable es
una opinión.

**Lo que haría falta y no se hizo:** que `nightshift resolve` guarde el commit o el PR en un
campo propio, no en prosa libre, y que el notario pase a ser un gate. Es una feature que no
está en el plan — la decide Matías, y hay una pregunta concreta esperándolo.

---

## RESUELTO — el instrumento de H17 medía un campo que la cadena real no matchea (2026-08-28)

`experimentos/08-el-techo-del-oraculo.py` lo encontró: H17 y el `07` armaban el bolsón de
frases como `signals + pattern + decisive_signal`, y `retrieve.candidates`

- **nunca** engancha contra `pattern`, y
- sí engancha contra `valid_when`, que el instrumento no miraba.

El único enganche del control al retenido *"el chequeo pasa porque su patrón no encontró
ningún archivo"* venía **sólo de `pattern`**: en la cadena real no existe.

**Corregido, y por decisión de Matías** —era su llamada porque mueve un número publicado en
la dirección que favorece al plugin (control 2 → 1). Se hizo entero y en un solo paso:

- `experimentos/camino_real.py`: la medición es el camino real —`promote_to_candidate`,
  `retrieve.candidates`, `retrieve.render`— y no hay bolsón de frases en ningún lado. El
  `07`, el `08` y H17 la comparten: **una sola definición de "engancha", la del plugin.**
- El veredicto de H17 se endureció en el mismo commit, y a propósito: ahora pide
  transferencia **y** control negativo en 0. Corregir un instrumento a favor propio y
  aflojar el criterio al mismo tiempo es cómo se fabrica un `PASS`.
- **H17 sigue en `FAIL`.** Ideado 2 de 3 retenidos contra 1 del control, con 1 prompt
  ajeno enganchado. La corrección no compró el veredicto.

---

## RESUELTO — lo que el techo del oráculo dijo del prompt de consolidación (2026-08-28)

Con la abstracción **esperada** —escrita a mano, con el retenido a la vista— los tres
síntomas enganchan y ningún ajeno, por el camino real y sin tocar `retrieve.py`. **La
cadena transporta.** Lo que faltaba estaba arriba, en `dream.PROMPT`, y se agregaron dos
reglas duras:

- `signals`, `valid_when` y `projected_signals` son la **única** superficie contra la que
  se busca; `pattern` no se matchea nunca. El modelo ponía ahí su mejor oración.
- Nombrar el mecanismo y no la herramienta. La única colisión del brazo ideado la carga
  una sola palabra: la proyección dice `linter` y el prompt ajeno también, por problemas
  distintos. En el oráculo, cambiar `linter` por `chequeo` lleva el falso positivo a 0.

`tests/test_ideate.py::SuperficieDeBusquedaTest` defiende las dos mitades: que el prompt lo
diga, y que `candidates` siga sin enganchar contra `pattern`. Si alguien cambia el ranking,
el test falla y el prompt no queda mintiendo en silencio.

**Lo que esto NO habilita, y es la parte que hay que respetar:** re-consolidar `cbbd7ff0`
con el prompt nuevo y anunciar que H17 pasó. El retenido se usó para diagnosticar; medir el
prompt nuevo contra él es entrenar contra el test. El prompt nuevo se evalúa sobre un corpus
que no participó de esto, y hasta entonces la mejora es **plausible y no medida**.

---

## Se corrió el control de ADR-004, y salió en contra (2026-08-28)

`experimentos/07-idear-contra-no-idear.py`. Contra un conjunto **retenido** —tres síntomas
de `cbbd7ff0` que una persona confirmó después, con paráfrasis escritas a mano— que
ninguno de los dos brazos vio:

| | transferencia (3 retenidos) | control negativo (3 ajenos) |
|---|---|---|
| `observed` | ~~2 de 3~~ → **1 de 3** | 0 |
| `ideate` | 2 de 3 | 1 |

**Los números del control se corrigieron el mismo día**, más abajo en este archivo: el
instrumento medía contra `pattern`, que la cadena real nunca matchea. Lo que sigue se
escribió con el empate delante y se deja como estaba, porque su conclusión no cambió — sólo
cambió cuál de las dos mitades la sostiene.

**Empate en transferencia, y una colisión de más para el brazo ideado.** La colisión: «el
linter se queja de un import sin usar» enganchó con la proyección sobre un linter cuya
lista de archivos quedó vacía, por compartir la palabra `linter`. Mismo sustantivo,
problema distinto — más débil que un falso positivo limpio, y el control no la hizo.

**Qué significa y qué no.** No refuta la hipótesis de ADR-004: la deja **sin sostener**,
que es distinto. n=1 corpus y tres retenidos no deciden nada. Pero hasta acá el proyecto
afirmaba el costo (el triple de tokens de salida, medido) contra un beneficio que nadie
había intentado medir, y ahora el primer intento no lo encuentra.

**Qué NO se hizo, y es deliberado:** apagar la ideación. Sería reaccionar a n=1 con la
misma ligereza con la que se prendió, y `idear` tiene además la evidencia de arriba —una
proyección que cerró un agujero real. Lo que corresponde es volumen, y es lo mismo que le
falta a todo lo demás de este repo.

La comparación se diseñó para no ser circular. Contar proyecciones por brazo sería trampa:
`observed` no puede producir ninguna, así que el brazo ideado gana por definición.
Preguntarle al brazo ideado por sus propias proyecciones sería peor: las escribió él. Por
eso el conjunto retenido y las paráfrasis humanas.

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

### El capítulo, a medias, el 2026-08-28

Matías pidió poder correr un ciclo de sueño **a demanda**, no sólo al cerrar la sesión.
Salió `nightshift sleep` (enmienda 0.3.8 de la spec).

**Lo que resuelve:** el borde. Sella la trayectoria en curso, consolida su grupo, y la
sesión sigue capturando en una nueva. Ya no hay que dejar de trabajar para consolidar lo
que se acaba de hacer.

**Lo que NO resuelve, y es la mitad difícil:** nightshift sigue sin poder *detectar* un
capítulo. El borde lo pone una persona. La idea que quedó escrita arriba —segmentar por el
desenlace, cada `make check` en verde y cada merge cierra uno— sigue sin abrirse, y ahora
tiene un motivo más para esperar: con `sleep` andando se puede **medir** si los bordes que
elige una persona producen candidatas mejores que un día entero, antes de escribir una
heurística que los adivine. Automatizar primero sería estimar en vez de medir, que es el
error que este archivo documenta tres veces.

**Lo que se acepta a cambio:** sellar parte la sesión en dos, que es exactamente lo que
spec §5.6 evita hacer en `Stop`. Es legítimo porque lo pide una persona en el borde que
elige, y no es gratis: una sesión mal cortada produce dos capítulos que ninguno cuenta la
historia entera. Nadie midió todavía cuánto cuesta eso.

**Y la primera corrida real encontró un bug que la suite no vio**, que es la única razón
por la que vale la pena escribir esto acá. `seal_chapter` guardaba `evidence or MARCA`, y
con un desenlace `tests_passed` —que trae evidencia propia— el marcador de "sellado a
demanda" desaparecía: justo en el caso informativo, que es donde más importa distinguir un
borde puesto a mano de uno puesto por `SessionEnd`. El test que había cubría sólo la rama
sin evidencia y pasaba en verde. Es el mismo modo de falla que este archivo documenta dos
veces más arriba, y esta vez lo encontró correr el comando sobre el propio repo, no leerlo.

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

---

## El esquema de intercambio es anterior al pivot: `export` pierde las tres ideas

**Encontrado el 2026-08-29, y lo encontró una conjetura del propio sistema.** La
proyección #14 de `5b3ff97f` decía: *«Exportar y reimportar el store fija la pérdida: el
campo ya no puede reconstruirse porque el canal lateral no viaja con el registro.»* Nadie
la había observado. Se fue a mirar y es cierta, sobre nightshift mismo.

`schema/trajectory.v1.json` declara `abstraction.additionalProperties: false` y admite
exactamente tres campos: `decisive_signal`, `pattern`, `signals`. El esquema se escribió
antes del pivot del 2026-08-27, y **nunca se extendió**. Entonces:

```sh
nightshift export 5b3ff97f    # sale 0
# abstraction: decisive_signal, pattern, signals
# projected_signals: 0 · physical_scene: ausente · diagram: ausente · logogram: ausente
```

El store **sí** tiene los cuatro campos —`nightshift why 5b3ff97f` los muestra enteros—,
pero no viajan. Un `export` seguido de un `import` devuelve una trayectoria sin ninguna de
las tres ideas: sin proyecciones, sin dibujo y sin escena. Sale 0, no avisa, y el registro
resultante es válido contra el esquema. Es el mismo mecanismo que la trayectoria que lo
predijo: *un objeto válido no es un objeto completo*.

**Qué toca esto que no es obvio.** H21 (*«se puede importar una cadena de ejecución
generada afuera»*) pasa, pero lo que importa llega mutilado: un CTE externo entra sin
proyecciones, o sea sin lo único que engancha con un síntoma **antes** de que ocurra.

**No lo arreglo en esta sesión** porque cambiar `trajectory.v1` es cambiar el contrato de
intercambio, y eso es una enmienda de spec con número, no un parche. Las opciones son dos
y las decide Matías: extender `v1` (rompe a cualquiera que valide estricto) o versionar a
`trajectory.v2` (y decidir qué hace `import` con un `v1`).

Queda escrito con la evidencia que lo motiva, y con la nota de que la primera conjetura
proyectada que se resolvió yendo a mirar el código **acertó**.

---

## El auditor trata un blob de 400 caracteres como si fuera una ruta

**Encontrado el 2026-08-29, y lo encontró el gate.** `make dogfood` pasó a rojo (exit 2)
con un hallazgo de `deny_path` en la trayectoria abierta de la propia sesión:

```
deny_path  trayectoria=16a5f7ff paso=36  campo=steps[36].result_summary  pos=0 len=400
```

**No es una fuga.** Lo capturado es la salida de un `grep` seguida del contenido de
`~/.nightshift/config.json` — o sea, la **lista de `deny_paths`**, no el contenido de
ningún archivo denegado. Lo que pasó es un artefacto de truncado:

```python
# el resumen se corta en max_result_summary_chars = 400, y cayó justo acá:
v[-25:] == 'ny_paths": [\n    "**/.env'
r.is_denied(v)        # True   ← el blob entero
r.is_denied(v[:-8])   # False  ← ocho caracteres menos y desaparece
# patrón que matchea: **/.env
```

`audit._scan_value` hace `redactor.is_denied(value)` sobre el **valor entero**
(`audit.py:123-124`), y `is_denied` usa `fnmatch`, donde `*` cruza saltos de línea. El
corte en 400 dejó la cadena terminando en `/.env`, así que 400 caracteres de texto
multilínea matchearon el glob de una ruta.

`audit.py:41-48` ya documenta exactamente esta tensión para el camino de *tokens* —«un
nombre suelto es una **mención**, no una ruta»— pero la rama del valor entero quedó sin
esa protección.

### Arreglado el 2026-08-29, autorizado por Matías, con test primero

La condición que faltaba no era una sino dos, y la segunda apareció al escribir el test de
la primera. Las dos se unificaron en un predicado, `audit._puede_ser_una_ruta`: `is_denied`
compara con `fnmatch`, así que sólo tiene sentido preguntarlo sobre un valor que **pueda
ser** una ruta.

1. **Sin saltos de línea.** `*` cruza `\n`, así que un blob multilínea cortado en `/.env`
   matchea `**/.env` como si el valor entero fuera esa ruta.
2. **Sin metacaracteres de glob.** `"deny_paths": ["**/.env", "**/.ssh/**"]` es la regla
   que *evita* la fuga, no una fuga. Una ruta real no lleva `*` ni `?`. Lo mismo del lado
   del tokenizador: un token pegado a un `*` es parte de un patrón.

**No afloja detección, y está medido, no afirmado.** Corriendo el auditor **anterior**
contra el store de hoy: **12 hallazgos**. El auditor **con el arreglo**, mismo store:
**6**. Los seis que desaparecen son todos patrones de glob y blobs truncados; ninguna ruta
real deja de detectarse, y hay dos tests de contrapeso que lo fijan (`x/.env` de una línea
sigue siendo hallazgo; una ruta negada embebida en prosa también).

Tests primero, y los dos salieron en rojo antes de tocar `audit.py`:
`test_un_blob_multilinea_no_es_una_ruta` y `test_un_patron_de_glob_no_es_una_ruta`.

### Lo que quedó rojo, y es otra clase

`make dogfood` **sigue en rojo**, y ya no por esto. Los hallazgos que quedan son **la
prosa de la propia sesión que arregló el bug**: `/.env` y `x/.env` escritos dentro de
comentarios, docstrings y `print`s de debug, capturados por nightshift mientras se
trabajaba.

**El del placeholder también se arregló** (autorizado el mismo día, con test primero). La
alternativa `[^\s,;)]{4,}` de `secret.assignment` es golosa y se lleva la puntuación
pegada, así que `token=<SECRET>|` no daba `fullmatch` y el placeholder del propio redactor
se marcaba como fuga. Lo que decide ahora no es que el valor *empiece* con un placeholder
—si alcanzara con eso, esconder un secreto sería prefijarlo— sino que, sacados los
placeholders, no quede nada que pueda **ser** un valor, con el mismo piso de 4 caracteres
que usa la regla. Hay contrapeso: `TOKEN=<SECRET>ghp_…` se sigue detectando.

**Y queda medida la propiedad incómoda, que es lo que vale la pena nombrar:** auditar una
sesión que trabaja sobre el auditor produce hallazgos de esa sesión. El conteo de esta
misma sesión, corrida tras corrida: **1 → 6 → 8 → 17**, y lo único que subía era cuánto
había escrito el agente sobre `.env`. El paso 95 son los hallazgos de la **pregunta que el
agente le hizo a Matías** para decidir qué hacer con los hallazgos. El gate de dogfooding
es autorreferencialmente frágil y no converge mientras se lo trabaja.

### Y la tercera sí bajó sensibilidad, por decisión de Matías (2026-08-29)

**`x/.env` en prosa es mención, no ruta.** Lo decidió Matías, y no es un bugfix: es una
decisión de spec sobre cuánto vale un falso negativo contra un falso positivo. **Lo que
cuesta, dicho con todas las letras: una fuga real de una ruta relativa embebida en una
oración ya no se detecta.**

Se pagó porque el gate no convergía mientras se lo trabajaba. La regla nueva
(`audit._es_una_ubicacion`) es que un token nombra un **lugar** sólo si está anclado —`/…`
o `~/…`— y tiene al menos un directorio antes del nombre. Entonces:

| token | antes | ahora | por qué |
|---|---|---|---|
| `/home/x/proj/.env` | hallazgo | hallazgo | es un lugar |
| `~/.ssh/id_rsa` | hallazgo | hallazgo | anclado, con directorio |
| `x/.env` en prosa | hallazgo | **mención** | relativo: lo que se decidió perdonar |
| `/.env` | hallazgo | **mención** | es `**/.env` sin su glob, y nombra la raíz |
| `args.file_path = "secrets/db.key"` | hallazgo | hallazgo | la rama del valor entero lo agarra igual |

Las dos últimas filas son las que impiden que la decisión sea más ancha de lo acordado, y
hay un test por cada una.

**Con esto el gate de M1 cerró:** `audit --min-sessions 5` sale 0 con cero hallazgos y
`make dogfood` sale 0. Vale registrar cómo cerró, porque el orden es el punto: se arregló
primero lo que era bug —midiendo que no se perdiera detección—, se paró antes de tocar lo
que no era bug, se preguntó, y recién entonces se aflojó, dejando escrito el costo. Cerrar
el gate aflojando el auditor sin ese orden habría sido fabricar un verde.
