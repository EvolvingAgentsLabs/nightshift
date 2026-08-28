# PREREG — Benchmark M4

| Campo | Valor |
|---|---|
| Estado | **BORRADOR — no congelado** |
| Congelado el | `TODO(Matias)` — fecha + commit hash |
| Umbrales fijados por | Matías. **No** Claude Code. |
| Se congela antes de | La primera línea de código de M1 |

## Por qué existe este archivo

Un umbral que se ajusta después de ver el resultado no es un umbral. Este documento
fija qué se mide, cómo se mide y qué cuenta como éxito **antes** de que exista el
código que se va a medir.

Reglas de congelamiento:

1. Mientras diga **BORRADOR**, se puede editar libremente.
2. Al congelarse se registra fecha y commit en la tabla de arriba, y a partir de ahí
   **cualquier cambio va al Registro de enmiendas** (§6) con motivo y fecha, antes de
   correr nada.
3. Claude Code **lee** este archivo. No propone, no completa ni ajusta umbrales.
   Todo `TODO(Matias)` lo resuelve una persona.
4. Si el benchmark se corre y el resultado no llega al umbral, el resultado es
   no-go. No se re-corre buscando una configuración mejor.

## 1. Qué decide M4

M4 es un **go/no-go**. Si no pasa, el proyecto se congela como spec (spec §11).

**Regla de decisión:** go si y sólo si

- mejora ≥ umbral pre-registrado en **al menos dos** de las tres familias A / C / D, **y**
- **cero regresión** frente a S0 en las tres familias, donde "cero regresión" significa
  no empeorar más de `TODO(Matias)` en ninguna métrica primaria.

## 2. Configuraciones comparadas (filas)

| Fila | Configuración | Disponible |
|---|---|---|
| `S0` | Claude Code + Auto Memory + Auto Dream **encendidos** | M4 |
| `S1` | S0 + nightshift, sólo trayectorias `candidate` | M4 |
| `S2` | S0 + nightshift, procedimientos `verified` | **Sólo tras M5** |

S0 es el baseline real: comparar contra un agente sin memoria sería comparar contra un
rival que ya no existe (ADR-001).

**Constantes en todas las celdas:** los mismos dos modelos, mismo seed de tareas, 3
corridas por celda, mismo límite de tool calls, misma máquina.

Son **dos** modelos y no uno, y conviene no confundirlos porque intervienen en momentos
distintos del experimento:

- El **modelo del agente** resuelve las tareas. Interviene en las dos filas: es el mismo
  en `S0` y en `S1`, porque lo que se compara es la memoria, no el agente.
- El **modelo de consolidación** corre dream y produce las `candidate`. Interviene
  **sólo en `S1`**: en `S0` no hay nightshift. Si cambia, cambia la calidad de lo que se
  inyecta, que es exactamente lo que la fila S1 aporta.

Dejarlos como una sola constante era un agujero: se podía congelar el pre-registro
fijando uno y dejando el otro suelto, y una corrida con otra consolidación no sería
comparable con la anterior. Ver ADR-003, que es lo que hizo visible la distinción.

- Modelo del **agente** — exacto y versión: `TODO(Matias)`
- Modelo de **consolidación** — backend (`claude-code` o `local`), modelo exacto y
  versión: `TODO(Matias)`
- **Estrategia de consolidación** (`observed` o `ideate`, ADR-004): `TODO(Matias)`

  `observed` abstrae lo que las trayectorias muestran. `ideate` idea primero el mecanismo
  como un dibujo, abstrae desde ahí, y **proyecta** síntomas que nadie observó — que
  entran al retrieval con la mitad del peso y anunciados como conjeturas.

  No es una preferencia: cambia qué **es** el brazo S1. Una corrida con una estrategia no
  es comparable con otra, y la que se congele acá es la que define qué se midió.

  **Actualizado el 2026-08-27 (enmienda 0.3.7 de la spec):** el código ya no ofrece las
  dos. `consolidation_strategy` dejó de ser una clave de config y `consolidate` idea
  siempre; `observed` sobrevive sólo como brazo de control de `experimentos/ideate.py`.
  La decisión de arriba sigue abierta y sigue siendo de Matías: congelar el pre-registro
  en `observed` es válido, y hoy costaría volver a abrir el interruptor a propósito.
  Escribirla sigue siendo obligatorio — el default del código no es una decisión de
  pre-registro.
- **Configuración de retrieval** — `max_injected`, `cross_repo`, y si se pre-registra el
  commit de la función de ranking (`retrieve.W_*`): `TODO(Matias)`

  Decide **qué se inyecta**, que es el tratamiento mismo. Es la misma clase de constante
  que el modelo de consolidación y la `consolidation_strategy`: dos corridas de `S1` con
  distinta configuración de retrieval no son comparables entre sí.

  No es una hipótesis. El 2026-08-27 el ranking cambió tres veces en una sesión —enganche
  por el fallo observado, la precondición como clave, y la bandera `decisive` apretada— y
  nada en este pre-registro habría dejado constancia de que el brazo `S1` cambió. La
  familia C lo tenía ya a la vista por otro lado: con `cross_repo` apagado, la fila `S1`
  llega al repo B con **cero** memorias, así que ese valor decide si la familia mide algo.
- Seed del set de tareas: `TODO(Matias)`
- Límite de tool calls por tarea: `TODO(Matias)`
- Presupuesto de wall-clock por tarea: `TODO(Matias)`

### 2.1 En qué se mide el presupuesto — decidido por Matías, 2026-08-27

**En tiempo de pared, y el criterio es la factibilidad por el camino directo.** No en
dinero: lo que el CLI reporta como costo viene a precio de lista (`costBasis: "list"`) y
con una suscripción de Claude Code no se factura, así que un tope en dólares no ataja
nada real. Los tokens miden consumo, pero no responden la pregunta que decide si M4 se
puede correr, que es si entra en una ventana sin nadie mirando.

Lo medido sobre 39 celdas ya corridas con agentes de verdad (los ensayos de las tres
familias, 2026-08-27):

| | por celda | las 102 celdas |
|---|---|---|
| mediana | 37,8 s | **1,1 h** |
| media | 43,3 s | 1,2 h |
| p90 | 70,5 s | 2,0 h |
| máximo observado | 97,8 s | 2,8 h |

**M4 entero entra en una noche, en serie, sin paralelismo.** La factibilidad no es el
cuello de botella: el pre-registro sí.

Lo que falta para cerrar el número —el tope por tarea, y si hay un tope para la corrida
entera— sigue abierto en la lista de arriba. Lo que ya no está en discusión es la unidad.

**Qué hace el runner con esto**, para que la decisión no viva sólo en un documento:

- `bench plan` proyecta las horas antes de arrancar, con la mediana y el p90 de las
  corridas que ya existen. Sin corridas previas lo dice en vez de estimar.
- `bench run --budget-minutes N` corta al agotarse la ventana, **al terminar una
  repetición**, nunca en el medio.
- La matriz va **repetición → fila** para que ese corte sea legítimo: las dos filas
  quedan con el mismo n. Con el orden anterior —fila → repetición— cortar dejaba S0
  entera y S1 a la mitad, que no es un experimento más chico sino uno torcido.
- Una corrida incompleta se lee hasta la última repetición completa en todas las filas;
  las celdas sueltas de la siguiente se descartan. Si no hay ninguna, no hay nada que
  comparar y el veredicto es indecidible, que no es no-go y sobre todo no es go.

## 3. Familias de tareas

### A — Bug recurrente variado  *(capacidad A: memoria procedimental)*

10 bugs con **causa compartida y síntoma distinto**, en un repo fixture.

- **Fase de aprendizaje:** las primeras `TODO(Matias)` tareas, en orden fijo.
- **Fase de medición:** las restantes.
- **Métrica primaria:** tasa de resolución en la fase de medición.
- **Métrica secundaria:** tool calls hasta el fix (mediana).
- **Criterio de resolución:** el gate del fixture sale 0 y salía ≠ 0 antes. Sin juicio
  de modelo.

| Métrica | Umbral de go (S1 vs S0) |
|---|---|
| Tasa de resolución | `TODO(Matias)` |
| Tool calls hasta el fix (mediana) | `TODO(Matias)` |

Repo fixture: `TODO(Matias)` — definir en M1, congelar acá antes de M4.

### C — Transferencia cross-repo  *(capacidad C)*

El mismo patrón estructural — pipeline con transformaciones opacas — en **dos repos
distintos**, sin nombres, paths ni dependencias compartidas.

- **Protocolo:** aprender en repo A, medir en repo B. Sin exposición previa a B.
- **Métrica primaria:** tasa de resolución en repo B.
- **Métrica secundaria:** tool calls hasta el fix en repo B (mediana).
- **Control obligatorio:** una celda con nightshift instalado pero con el store vacío,
  para separar la ganancia de la memoria de la ganancia del prompt de inyección.

| Métrica | Umbral de go (S1 vs S0) |
|---|---|
| Tasa de resolución en repo B | `TODO(Matias)` |
| Tool calls hasta el fix en repo B (mediana) | `TODO(Matias)` |

Repos A y B: `TODO(Matias)`.

### D — Precisión de consolidación  *(capacidad D)*

Se inyectan **contradicciones y reversiones** en el histórico y se mide cuánta de la
memoria inyectada es falsa o stale al final de la corrida.

- **Métrica primaria:** proporción de memorias inyectadas que son falsas o stale.
  **Menor es mejor** — el umbral es una reducción, no un aumento.
- **Definición de "falsa":** contradice el estado del repo en el commit de la tarea.
- **Definición de "stale":** fue verdadera y dejó de serlo por una reversión posterior
  presente en el histórico.
- La clasificación falsa/stale la hace un **script determinista** contra un ground
  truth construido a mano al preparar el fixture, no un modelo.

| Métrica | Umbral de go (S1 vs S0) |
|---|---|
| Proporción de memorias falsas o stale | `TODO(Matias)` |

M5 reevalúa esta familia con `verify` (fila S2). El gate propio de M5 es que la
precisión de `procedure` supere a la de `candidate`; si verificar no separa mejor que
no verificar, verificar no sirve (ADR-002).

### E — Abstención  *(la mitad de la conducta que A, C y D no pueden ver)*

Entró el **2026-08-28, por decisión de Matías**, después de que
`experimentos/10-abstencion.py` midiera que dream **no se abstiene**: contra tres
trayectorias sin nada en común —un margen de CSS, un índice faltante en una base, una coma
de más en un JSON— encontró un patrón **3 de 3 veces**.

Las familias A, C y D tienen la causa compartida **plantada a mano**: A es un normalizador
roto que rompe diez módulos, C es la misma etapa que se traga la excepción en dos repos.
Miden si dream encuentra un mecanismo que alguien puso para que encuentre, y por
construcción **no pueden detectar el fallo contrario**. Un consolidador que nunca dice que
no vuelve no informativos a todos sus "sí", y ningún resultado favorable de las otras tres
familias lo descarta.

- **Grupos sin patrón:** trayectorias de dominios, mecanismos y desenlaces distintos.
- **Grupos con patrón:** control obligatorio. Sin él, un modelo que contesta `null` siempre
  pasaría la familia con nota perfecta, y sería inútil.
- **Métrica primaria:** tasa de abstención correcta sobre los grupos sin patrón.
- **Métrica secundaria:** tasa de abstención **incorrecta** sobre los grupos con patrón —
  el precio del piso, pagado en recall.
- **Criterio:** `pattern` nulo o vacío en la respuesta del modelo. Sin juicio de modelo y
  sin lectura humana.

| Métrica | Umbral de go |
|---|---|
| Tasa de abstención correcta (grupos sin patrón) | `TODO(Matias)` |
| Tasa de abstención incorrecta (grupos con patrón) | `TODO(Matias)` |

Corpus: `TODO(Matias)` — hay un fixture construido en `bench/fixtures/familia-e/`, con la
misma advertencia que los otros tres: es una propuesta, los identificadores los fija una
persona.

Esta familia **no compara S0 contra S1**: no mide si la memoria ayuda, mide si el
consolidador puede decir que no. Es un piso, no un umbral de mejora, y por eso su go/no-go
se lee distinto que el de A, C y D.

## 4. Cómo se reporta

Una tabla por familia, filas S0/S1, tres corridas por celda: mediana y rango.
Se publican **todas** las corridas, incluidas las que salieron mal. Sin selección
post-hoc de corridas.

Estadística: `TODO(Matias)` — decidir si se reporta test de significancia o sólo
mediana + rango, y dejarlo escrito antes de congelar. Con n=3 por celda, `TODO(Matias)`
debe reconocer explícitamente el poder estadístico disponible.

## 5. Amenazas a la validez (a mitigar antes de congelar)

| Amenaza | Mitigación |
|---|---|
| Contaminación: el fixture está en los datos de entrenamiento del modelo | `TODO(Matias)` |
| El efecto viene del texto inyectado y no de la memoria | Celda de control con store vacío (familia C) |
| Auto Dream corre en distinto estado entre filas | `TODO(Matias)` — protocolo de reset entre corridas |
| Orden de tareas favorece a S1 | Orden fijo por seed, idéntico en todas las filas |
| El operador ve resultados parciales y ajusta | Corridas por lote, sin inspección intermedia |

## 6. Registro de enmiendas

Vacío. Toda enmienda posterior al congelamiento va acá, con fecha, motivo y qué cambió.

| Fecha | Qué cambió | Motivo |
|---|---|---|
| — | — | — |
