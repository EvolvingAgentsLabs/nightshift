# Familia A — bug recurrente variado

Repo fixture candidato para la familia A del benchmark (PREREG §3-A): **10 bugs con causa
compartida y síntoma distinto**.

> **Falta congelarlo.** `bench/PREREG.md` dice `Repo fixture: TODO(Matias)`. Este
> directorio es una propuesta construida para que M4 pueda correr el día que el
> pre-registro se congele; los identificadores los fija Matías, no un agente.

## El diseño

Una sola función — `registro/texto.py::normalizar` — decide qué significa "la misma
clave" para todo el paquete. Tiene dos agujeros: no colapsa espacios internos y no saca
los caracteres de ancho cero. Ninguno de los dos se ve leyendo los datos.

Diez módulos la usan, y cada uno rompe distinto:

| Tarea | Módulo | Síntoma que ve quien reporta el bug |
|---|---|---|
| `test_01_indice` | `indice.py` | `buscar()` levanta `KeyError` con una clave que está |
| `test_02_dedup` | `dedup.py` | quedan duplicados que deberían haberse colapsado |
| `test_03_orden` | `orden.py` | el orden alfabético sale mal y no se ve por qué |
| `test_04_union` | `union.py` | el join pierde filas en silencio |
| `test_05_cache` | `cache.py` | el cache no acierta nunca y todo se recalcula |
| `test_06_grupo` | `grupo.py` | un grupo aparece partido en dos |
| `test_07_csvio` | `csvio.py` | el ida y vuelta por CSV no devuelve la misma clave |
| `test_08_busqueda` | `busqueda.py` | la búsqueda no encuentra algo que está |
| `test_09_reporte` | `reporte.py` | los totales no cierran: un cliente aparece dos veces |
| `test_10_validacion` | `validacion.py` | una fila válida se rechaza |

**Por qué esta forma.** La capacidad A es memoria procedimental: recordar *cómo se
averiguó*, no *qué era verdad*. Diez síntomas distintos con una causa común es el caso
donde eso se nota — la memoria declarativa guarda "el bug estaba en `texto.py`", que ya
no sirve cuando el síntoma cambia; la procedimental guarda "cuando dos claves idénticas a
la vista no matchean, mirá los invisibles en el normalizador", que sirve las diez veces.

Cada celda del benchmark arranca de una copia limpia del repo (el runner la hace), así
que el agente tiene que volver a encontrar la causa en cada tarea.

## Verificarlo

```sh
nightshift bench fixtures            # los 10 fallan antes y pasan con el fix de referencia
```

Un fixture donde una tarea ya pasa no mide nada: `test_03_orden` empezó así —el carácter
de ancho cero ordena *después* de las letras, no antes— y lo encontró ese comando.

## Lo que no está acá

El fix de referencia (`.referencia/texto-arreglado.py`) existe **sólo** para que el
comando de arriba pueda afirmar que cada tarea es resoluble. No es la solución esperada
del agente ni se le muestra: si alguna vez aparece en el prompt de una tarea, el
benchmark dejó de medir lo que dice medir.
