# Familia G — el procedimiento que falla en el paso 7

Fixture candidato para una familia nueva: **un procedimiento largo cuyo conocimiento no es
ningún hecho, es el orden.**

> **Falta congelarlo.** No hay sección de esta familia en `bench/PREREG.md` todavía: entra
> el día que Matías la abra, con sus umbrales. Este directorio es la propuesta construida.

## De dónde sale

De la primera de las tres ideas, que hoy no tiene ninguna tarea que la ejercite:

> **CTE — la cadena de pensamiento es la cadena de ejecución.** Lo que sobrevive de un
> trabajo no es un monólogo interno: es la secuencia que tocó el filesystem.

Las familias A, C y D son bugs de una sola causa. Ahí la memoria óptima es un **hecho** —
*"el normalizador no saca los caracteres de ancho cero"*— y una memoria declarativa lo
guarda igual de bien. Esta familia elige el género donde el hecho, solo, **no sirve**:
*"necesita `MIGRACIONES_MODO=estricto`"* es inútil si no sabés que eso aparece recién
después de crear `.estado/revision`, y que después viene otra cosa.

Es también el género donde una persona siente alivio en vez de leer una tabla: nadie
documenta los releases, todos los rederivan, y el fallo aparece a los veinte minutos de
setup.

## El diseño

Un release de doce pasos. Se corta en el 7, y el mensaje dice **qué chequeo no pasó y nunca
qué hacer para que pase** — que es cómo se ven los scripts de release escritos por alguien
que ya sabía.

La cadena, que sólo se descubre de a un eslabón por corrida:

| Corrida | Dónde se corta | Lo que hacía falta saber |
|---|---|---|
| 1 | paso 7 | `.estado/revision` no existe |
| 2 | paso 7 | `MIGRACIONES_MODO=estricto` |
| 3 | paso 7 | la revisión base tiene que coincidir con `app/VERSION` |
| 4 | paso 8 | `FIRMA_KEY` |
| 5 | — | 12/12 |

**Cuatro corridas para alguien que no lo sabe. Una para alguien que sí.** Y no hay forma de
adivinar el eslabón 2 antes de resolver el 1: el script no lo menciona hasta que llega ahí.

## La métrica, y se cuenta sola

- **Primaria: `corridas_del_release_hasta_verde`.** El propio `release.sh` la escribe en
  `repo/.estado/corridas`. Determinista, sin juicio de modelo, sin contar tool calls.
- **Secundaria:** wall-clock hasta el gate en verde. Es lo que siente una persona, y es lo
  único que esta familia mide mejor que ninguna otra.

El piso teórico es 1 y el techo sin memoria es 4. Un rango de 1 a 4 en una métrica entera y
sistemática es exactamente lo que a las familias A, C y D les falta: ahí todos los brazos
resuelven y la diferencia se pierde en el ruido.

**Reset obligatorio entre corridas:** `rm -rf repo/.estado`. Está en `fixture.json`, y sin
él la segunda celda arranca con el trabajo de la primera hecho.

## La memoria que se siembra

`historia.json` tiene **una** trayectoria: la cadena del release anterior, con sus cuatro
fallos y sus cuatro correcciones en orden. No hay abstracción que valga acá — lo que
transfiere es la secuencia, y por eso es la familia que mide CTE y no las otras dos ideas.

## Cómo se corre

```sh
sh bench/fixtures/familia-g/gate.sh     # 7 la primera vez; imprime cuántas corridas van
rm -rf bench/fixtures/familia-g/repo/.estado    # reset
```

## Lo que esta familia no dice

No dice nada sobre proyección ni sobre ideación: las conjeturas de un release no son el
punto. Mide una sola de las tres ideas, y la mide sola a propósito.
