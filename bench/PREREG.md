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
