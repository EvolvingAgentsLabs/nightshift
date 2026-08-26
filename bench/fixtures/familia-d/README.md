# Familia D — precisión de consolidación

Fixture candidato para la familia D (PREREG §3-D): se inyectan **contradicciones y
reversiones** en el histórico y se mide cuánta de la memoria inyectada es falsa o stale.

> **Falta congelarlo**, como los otros dos.

## Las piezas

| Archivo | Qué es |
|---|---|
| `historia.json` | Cuatro trayectorias con su afirmación (`claim:cNN`), sembradas antes de cada tarea |
| `verdad.json` | El ground truth, hecho a mano: qué afirmación está vigente, cuál es stale y cuál es falsa |
| `sembrar.py` | Deja el histórico en un store propio de la celda (`.store/`) |
| `clasificar.py` | Compara lo inyectado contra el ground truth y emite `false_stale_ratio` |
| `servicio/` + `tests/` | Tres bugs con causa compartida, para que también se mida resolución |

Las cuatro afirmaciones, y por qué cada una:

- **c01 — vigente.** Los límites se cambian en `ajustes.py` y toma efecto. Es verdad.
- **c02 — stale.** "El límite vive hardcodeado en el cliente." Fue verdad hasta que los
  límites se movieron a `ajustes.py`. Lo que queda hardcodeado es el bug, no la forma de
  configurarlo. Es el caso que Auto Dream borraría y nightshift conserva enlazado.
- **c03 — falsa.** "Subir todo a 30 segundos lo resuelve." Se probó, el usuario la
  revirtió, y contradice el estado del repo en el commit de la tarea.
- **c04 — vigente.** "Cuando cambiar la configuración no cambia nada, buscá un valor
  escrito a mano en el llamador." Es el procedimiento, no el hecho: sigue aplicando.

La clasificación la hace `clasificar.py` — determinista, sin modelo, como pide §3-D.

## El agujero que este fixture NO tapa

`clasificar.py` **sólo puede medir la fila S1.** En S0 nightshift no está, y las memorias
que inyecta Auto Memory no son visibles desde acá: no hay API, y leerlas sería escribir en
territorio de la memoria nativa, que ADR-001 prohíbe tocar.

Cómo se enumeran las memorias inyectadas en S0 es un **`TODO(Matias)`** que el
pre-registro todavía no resuelve. Mientras no exista, S0 no emite dato y la familia D
queda **indecidible** en el reporte — que es lo correcto: sin baseline no hay comparación,
y un veredicto inventado es peor que ninguno.

## Correrlo

El runner exporta `NIGHTSHIFT_BENCH_STORE`, que vive por **(fila, repetición)** y no por
celda: dentro de una repetición la memoria se acumula tarea a tarea. `sembrar.py` deja el
histórico ahí y el adaptador apunta `NIGHTSHIFT_HOME` al mismo lugar.

Ojo con lo que eso implica para esta familia: el histórico se siembra **antes de cada
tarea** sobre un store que ya trae lo capturado por las tareas anteriores de la misma
repetición. Es a propósito — mide la precisión de lo inyectado en una sesión que además
viene aprendiendo — pero si el protocolo quisiera un store limpio por tarea, eso es parte
de lo que hay que congelar en PREREG.
