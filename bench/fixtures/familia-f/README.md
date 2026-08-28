# Familia F — la trampa sistemática

Fixture candidato para una familia nueva: tareas donde **el arreglo localmente obvio es
justo el que ya se probó y se descartó**.

> **Falta congelarlo.** No hay sección de esta familia en `bench/PREREG.md` todavía: entra
> el día que Matías la abra, con sus umbrales. Este directorio es la propuesta construida,
> igual que los de las familias A, C, D y E.

## De dónde sale, y qué problema resuelve

Los experimentos 01, 03 y 04 llegaron al mismo muro por separado: **todos los brazos
resuelven la tarea**, la métrica primaria tiene varianza cero, y lo único que queda es
contar tool calls, donde el ruido entre corridas idénticas (8, 13, 10 en la *misma* tarea
sin ninguna memoria) tapa cualquier efecto. El diagnóstico que se sacó fue "hace falta
n=3". Es el diagnóstico equivocado: **no falta n, falta que el brazo sin memoria fracase**.

Un fallo que ocurre a veces se pierde en el ruido. Un fallo **sistemático** se separa con
tres corridas. Por eso esta familia no elige tareas difíciles: elige tareas con **trampa**.

Y es, además, la única familia que mide lo que el README promete y ninguna otra ejercita:

> No *"el timeout está en 2000"* —una memoria declarativa sabe eso— sino *"eso ya se probó,
> alguien subió el límite, lo corrigieron porque tapaba el síntoma, y ese camino descartado
> seguía siendo correcto cuando el límite estaba genuinamente bajo."*

Hoy **ninguna tarea del benchmark mide esa frase.**

## El diseño

Tres bugs. Cada uno tiene, a la vista y cerca del error, una perilla en
`servicio/ajustes.py` que parece el arreglo.

| Tarea | Síntoma | La trampa | ¿La trampa pasa el test del síntoma? | La causa real |
|---|---|---|---|---|
| `reconciliacion` | se cae con lotes de más de 500 | subir `TIMEOUT_SEGUNDOS` | **sí** | una llamada al libro por movimiento, en vez de una por lote |
| `envio` | el proveedor recibe el aviso dos veces | bajar `MAX_REINTENTOS` | no — es una pista falsa, y cuesta una vuelta igual | el reintento manda un envío nuevo: falta clave de idempotencia |
| `precio` | el precio en dólares devuelve el valor en pesos | apagar el cache con `TTL = 0` | **sí** | la clave del cache no incluye la moneda |

**El gate tiene dos mitades y ésa es toda la idea.** `tests/test_politica.py` afirma que los
tres límites no cambiaron: son política del servicio, no perillas. Un arreglo que tapa el
síntoma moviendo un número pasa el test del síntoma y **falla el de política**, así que el
gate sale ≠ 0 y la trampa queda registrada de forma determinista, sin que ningún modelo
juzgue nada.

La tarea `precio` tiene además un segundo detector que no depende de la constante:
`test_el_cache_sigue_sirviendo` falla si el cache dejó de acertar. Apagar el cache hace
pasar el test del síntoma y rompe ése.

## La métrica, y por qué no son tool calls

- **Primaria: `primer_intento_sin_trampa`.** Binaria por tarea: ¿la primera corrida del gate
  después del arreglo del agente pasó, o falló por `test_politica`? Es sistemática, no
  ruidosa, y con tres corridas por celda se separa.
- **Secundaria:** tool calls hasta el gate en verde. Se reporta y no decide nada, por lo
  mismo que en las otras familias.

## La memoria que se siembra

`historia.json` tiene las seis trayectorias de la fila S1: por cada bug, **la alternativa
descartada con su precondición** y la que la reemplazó. Es exactamente la capacidad B —lo
contradicho sobrevive enlazado, no se borra— y es lo que el brazo S0 no tiene.

Las precondiciones son la parte que hace que esto sea conocimiento y no ruido. *"Subir el
timeout"* sigue siendo correcto **cuando el límite estaba genuinamente bajo y el costo por
llamada no crece con el lote**; lo que estaba mal no era la perilla, era el diagnóstico.

## Cómo se corre

```sh
sh bench/fixtures/familia-f/gate.sh     # 1 con los bugs, 0 cuando están arreglados
```

Los arreglos de referencia están en `.referencia/`, uno por tarea. Con los tres aplicados el
gate sale 0.

## Lo que esta familia no dice

No dice que la memoria sirva en general: dice si sirve **donde el error es sistemático**, que
es el único lugar donde tres corridas alcanzan para verlo. Y no reemplaza a la familia A —
mide otra cosa, y la A sigue midiendo si el patrón transfiere entre síntomas.
