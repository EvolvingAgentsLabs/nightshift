# Familia C — transferencia cross-repo

Repos fixture candidatos para la familia C (PREREG §3-C): el **mismo patrón estructural**
en dos repositorios distintos, sin nombres, rutas ni dependencias compartidas.

> **Falta congelarlo.** `bench/PREREG.md` dice `Repos A y B: TODO(Matias)`. Esto es una
> propuesta construida; los identificadores los fija Matías.

## El patrón

Un pipeline aplica una lista de etapas a cada registro, y **una etapa se traga la
excepción** y devuelve un registro vacío. El síntoma aparece lejos de la causa: promedios
en cero, filas ausentes, rótulos vacíos, y ningún error en ningún log.

| Repo | Dominio | Módulo | Qué reporta el usuario |
|---|---|---|---|
| `repo-alfa` | lecturas de sensores | `recolector/cadena.py` | el promedio da 0 · los rótulos salen vacíos |
| `repo-beta` | fichas bibliográficas | `catalogo/secuencia.py` | faltan libros en el listado · encabezados en blanco |

**Protocolo:** las dos tareas de `repo-alfa` son la fase de aprendizaje; las dos de
`repo-beta`, la de medición. El fixture declara `"fixed_order": true` justamente por eso:
la rotación por seed metería tareas del repo B en la fase de aprendizaje, que es la
exposición previa que el protocolo prohíbe.

## Lo que los separa

Los dos repos no comparten ni el nombre del directorio de tests (`tests/` contra
`pruebas/`). Está testeado: `tests/test_fixtures.py` afirma que no comparten
identificadores fuera de una lista corta de la stdlib.

Suena excesivo hasta que se piensa qué mide la familia C. Si el test del repo B usa las
mismas palabras que el del A, un agente puede "transferir" leyendo el test — y entonces la
métrica dejó de medir la memoria y pasó a medir la coincidencia de vocabulario.
