# Familia E — abstención

Fixture candidato para la familia E (PREREG §3-E): **¿dream dice que no cuando no hay
patrón?**

> **Falta congelarlo**, como los otros tres. `bench/PREREG.md` dice
> `Corpus: TODO(Matias)` y los dos umbrales están sin fijar. Este directorio es una
> propuesta construida para que la familia pueda correr el día que el pre-registro se
> congele.

## De dónde sale

De un resultado, no de una idea. `experimentos/10-abstencion.py` le dio a dream tres
trayectorias sin absolutamente nada en común —un margen de CSS que se corre, un índice
faltante en una base, una coma de más en un JSON— y **encontró un patrón las tres de tres
veces** que se le preguntó. Lo que encontró era cierto y vacío: *"el fallo se reporta en la
coordenada donde el estado inválido se consume"*, que es una descripción de casi cualquier
bug.

Las familias A, C y D no pueden ver esto. Están construidas con la causa compartida
**plantada a mano**: A es un normalizador roto que rompe diez módulos con diez síntomas, C
es la misma etapa que se traga la excepción en dos repos. Miden si dream encuentra un
mecanismo que alguien puso ahí para que lo encuentre, y nunca la mitad contraria. Un
consolidador que no sabe abstenerse vuelve no informativos a todos sus "sí" — y ningún
resultado favorable de las otras tres familias descarta esa posibilidad.

## El diseño

Cuatro grupos de tres trayectorias, y las dos mitades hacen falta.

| Grupo | Se espera | Por qué |
|---|---|---|
| `sin-01` | `{"pattern": null}` | CSS, un índice de base y un JSON: ni dominio, ni mecanismo, ni desenlace |
| `sin-02` | `{"pattern": null}` | La trampa difícil: tres trabajos que **sólo** comparten género —son bugs— con un mecanismo distinto cada uno |
| `con-01` | un patrón | Un valor por defecto que enmascara la ausencia del dato: cupón inexistente, edad nula, backoff vacío |
| `con-02` | un patrón | Una comparación que normaliza de un lado y no del otro: mayúsculas, espacios, acentos |

**Sin los grupos `con-`, esto no mide nada:** un modelo que contesta `null` siempre pasaría
la primera mitad con nota perfecta y sería completamente inútil. La familia mide las dos
tasas y las reporta por separado, porque el piso se paga en recall y el precio tiene que
verse.

`sin-02` existe porque `sin-01` es demasiado fácil de aprobar por accidente. Tres trabajos
de dominios obviamente distintos invitan a decir que no; tres bugs que *podrían* compartir
algo —todos tienen un fallo que aparece lejos de su causa— son donde un consolidador
complaciente se delata. Compartir género no es compartir mecanismo, y ésa es exactamente la
distinción que la familia mide.

## Cómo se corre hoy

El runner de esta familia no existe todavía: `nightshift bench` se niega a correr hasta que
`PREREG` esté congelado, y eso no cambia. Lo que sí corre es el experimento del que salió
el fixture, con dos de estos cuatro grupos:

```sh
make abstencion          # 3 repeticiones, 6 llamadas al modelo
```

## Lo que esta familia no dice

No dice si la memoria sirve — eso era M4 y sigue sin medirse. No compara S0 contra S1: no
hay dos filas, porque abstenerse no es una mejora sobre no tener memoria. Es un **piso**, y
lo que responde es si el consolidador **puede** decir que no.
