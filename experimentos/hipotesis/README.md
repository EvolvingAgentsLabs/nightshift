# Hipótesis, una por archivo

La cola de trabajo del pivot, hecha script. Cada archivo valida **una** hipótesis del
proyecto y nada más.

```sh
nightshift experiments              # todas
nightshift experiments --only H03   # una
python3 experimentos/hipotesis/H03-el-primer-eslabon-se-ancla.py   # también corre sola
```

## Los tres estados, y por qué son tres

- **`PASS`** significa que **se comprobó**, ejercitando el código. Un experimento que no
  ejercita nada no es un experimento: es una opinión con nombre de archivo.
- **`FAIL`** es un resultado, no un error. Es la lista de lo que falta, y es el punto.
- **`BLOCKED`** es distinto de `FAIL`: la hipótesis no se puede comprobar todavía porque
  depende de una decisión humana o de material que no existe. Confundirlos convierte una
  espera en un fracaso, y este repositorio ya pagó esa confusión.

`nightshift experiments` sale 1 si hay algún `FAIL`. Un `BLOCKED` no rompe el gate: lo
espera.

## Reglas para escribir uno

1. **Nunca toca el store real.** `StoreDesechable` abre uno nuevo en un `HOME` temporal.
   Un experimento que escribe en `~/.nightshift` deja de ser reproducible en la segunda
   corrida, y peor: ensucia la evidencia con la que el proyecto decide.
2. **El detalle de un `FAIL` dice qué falta y por qué no está**, no sólo que falta. Es lo
   que hace que otra sesión pueda tomarlo sin releer el plan entero.
3. **Un experimento que se rompe cuenta como `FAIL`.** Un error de importación no puede
   leerse como "todavía no lo implementamos".
4. **Uno por hipótesis.** Si un archivo comprueba dos cosas, cuando falle no se va a saber
   cuál.

## El ciclo de trabajo

En cada iteración: recorrer la lista, tomar los `FAIL`, y al terminar cerrar la sesión y
correr un ciclo de sueño (`nightshift sleep`) para que lo que se hizo entre a la memoria
del propio proyecto.
