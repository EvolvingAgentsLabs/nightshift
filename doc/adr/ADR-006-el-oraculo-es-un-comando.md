# ADR-006 — El oráculo es un comando, no un servicio

| Campo | Valor |
|---|---|
| Estado | Aceptado |
| Fecha | 2026-08-28 |
| Reemplaza | nada. Extiende ADR-003 a un caso que ADR-003 no había decidido |
| Relacionado | ADR-002 (`verify`), ADR-003 (el modelo de dream), ADR-004 (proyección) |

## Contexto

Dream proyecta conjeturas: síntomas que **nadie observó**. Hasta el 2026-08-28 nada las
cerraba, y el propio README lo decía: *«una conjetura que nadie resuelve no es memoria, es
una nota»*. Con F1 apareció el primer oráculo —una persona tecleando `nightshift resolve`—
y con él la pregunta que este ADR decide: **quién más puede resolver una conjetura, y cómo
entra sin romper nada.**

Matías lo pidió en términos más amplios: incorporar CoT, CoT de imaginación y CTE
**generados afuera** al mecanismo de sueño, con influencia de un oráculo externo, para
agregar comportamiento que el modelo no produce solo.

La restricción es dura y no la puso este ADR. **ADR-003:** ningún módulo de `nightshift/`
habla por red, y no se agregan dependencias que exijan una API key nueva. `make lint-code`
lo verifica. Un oráculo remoto llamado por nightshift viola las dos.

Y hay una segunda restricción, del lado de la evidencia: el proyecto entero se apoya en
una jerarquía —**observado > inferido > conjeturado**— y en que nada llegue a `procedure`
sin `verify`. Un oráculo que devuelve veredictos sin origen la disuelve tan bien como un
modelo que inventa.

## Decisión

**Un oráculo es un ejecutable del usuario que lee una pregunta por stdin y escribe un
veredicto por stdout.** El mismo patrón que ya usa el modelo desde ADR-003, con el mismo
motivo: nightshift invoca un proceso, no una API.

- Se configura en `oracle_command`, igual que `model_command`.
- El contrato es deliberadamente chico —`{"projection", "pattern"}` entra,
  `{"status", "evidence"}` sale, con `status` en `confirmed | refuted | open`— para que
  escribir un oráculo sea media hora y no un proyecto.
- **Un veredicto sin evidencia se rechaza**, igual que el de una persona. Y el autor queda
  escrito: un veredicto sin autor no se puede revisar.
- **Un oráculo roto es un error, nunca un `open`.** Confundirlos convertiría una falla de
  plomería en un dato, que es la forma exacta en que este repositorio ya perdió dos
  milestones.

Con eso, tres oráculos son el mismo mecanismo con distinto ejecutable: la persona
(`resolve`), git (`corroborate`) y cualquier cosa que enchufe el usuario.

**El oráculo de git decide algo aparte y se llama distinto a propósito.** Lee la historia
del repositorio —¿el commit sigue siendo ancestro de HEAD?, ¿lo revirtieron?— y produce una
**corroboración**, no una verificación. `verify` (ADR-002) reproduce una trayectoria contra
un gate declarado; esto lee historia. Una candidata que sobrevivió sigue siendo
`candidate`, sigue pesando lo mismo y sigue sin estar verificada. Si esa distinción se
afloja, el proyecto pasa a decir que verifica cuando no verifica.

**Lo importado tiene clase de origen.** `nightshift import` acepta un `trajectory.v1`
producido afuera, le pone `origin = external`, le baja el peso por debajo de cualquier fila
local, lo vuelve a redactar de este lado y lo anuncia en el encabezado de la inyección.

## Consecuencias

Lo que esto cuesta, dicho antes y no después.

**La credencial y el riesgo pasan a ser del usuario.** Si alguien envuelve una API remota
en su `oracle_command`, sus trayectorias salen de la máquina — y nightshift no puede
impedirlo ni sabe que pasó. Lo que sí queda garantizado es lo que el proyecto puede
garantizar: `nightshift/` no habla con la red, y el linter lo verifica. La frontera es
explícita en vez de imaginaria.

**Un oráculo automático puede resolver mal, a escala.** Una persona resuelve tres
conjeturas por sesión; un comando puede resolver diecinueve en un minuto. Por eso el autor
se guarda (`oracle:<ejecutable>`) y por eso el auditor falla ante una resolución sin
origen: cuando un oráculo resulte malo, hay que poder encontrar y revisar todo lo que dijo.

**Corroborar sólo funciona desde el repo que produjo la trayectoria.** El store guarda el
fingerprint del repositorio y no su ruta (schema §repo_fingerprint), a propósito. Adivinar
de qué repo se trata sería inventar procedencia, así que desde otro repo la respuesta es
`unknown` — y `unknown` es una respuesta, no un fallo.

**Lo externo pesa menos, y el número lo decide una persona.** `EXTERNAL_WEIGHT_CAP = 0.2`
queda por debajo de una trayectoria cruda local (0.3) y de una `candidate` (0.6). El valor
exacto es de la misma clase que `W_PROJECTED_MATCH` y lo fija Matías; **la desigualdad no
se negocia**: lo que no se observó en esta máquina no puede desplazar a lo que sí.

**Y un CoT externo no es un CTE.** No ejecutó. Importar un razonamiento como si fuera una
cadena de ejecución es el modo de falla de la candidata `1f94f424` —abstraer un mecanismo
inexistente a partir de texto que el repositorio decía de sí mismo— institucionalizado y a
escala. El comando lo advierte; el esquema no lo puede impedir.

## Alternativas consideradas

**Un cliente HTTP dentro de `nightshift/`, con la key en la config.** Es lo más cómodo y
choca de frente con ADR-003. Se descarta: la garantía «este código no habla con la red» es
verificable por un linter y vale más que la comodidad. Si alguna vez hace falta, entra
envuelta en un `oracle_command` que escribe el usuario.

**Que el oráculo pueda ascender una `candidate` a `procedure`.** Se descarta. Eso es
`verify` (ADR-002) y tiene un requisito que un oráculo no cumple: reproducir contra un gate
que sale 0 o distinto de 0. Un oráculo que puede ascender vuelve opcional la única
condición que el proyecto no negocia.

**Un cuarto estado, «probablemente».** Se descarta. El valor de resolver es que **obliga a
decidir**, y lo que todavía no se sabe ya tiene estado: `open`.

**Importar sin clase de origen, confiando en la redacción del que exportó.** Se descarta.
Que el otro diga que redactó no es comprobable desde acá, y aceptarlo sería importar el
criterio de otra máquina junto con los datos.
