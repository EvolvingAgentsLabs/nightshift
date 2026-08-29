# Bitácora — qué pasó de verdad, en su tamaño real

Estas secciones vivían en [`README.es.md`](../README.es.md). Se movieron acá el
2026-08-29 para que el README quedara corto: esto es la versión larga, entera, no un
resumen de ella. Nada de esto está verificado — `verify` es M5 y no existe.

*[In English](LOGBOOK.md)*

## La noche en que soñó sobre sí mismo

El 2026-08-27 a las 15:25 UTC el plugin consolidó el store de su propio desarrollo y, desde
el dibujo del mecanismo, **proyectó cuatro síntomas que nadie había observado**
([ADR-004](adr/ADR-004-ideacion-y-proyeccion.md)). Esa misma tarde, midiendo por otro
motivo, dos resultaron ciertos:

| Lo que dream proyectó | Lo que se midió horas después |
|---|---|
| «El retrieval devuelve coincidencias por forma estructural sin relación con el contenido del trabajo.» | Dos prompts con síntomas distintos devolvían el mismo orden y los mismos scores |
| «Una revisión manual de un registro reciente muestra la estructura completa y todos los campos de texto en blanco.» | El prompt del propio dream mostraba seis pasos `(sin resumen)` de una trayectoria de 400 pasos que tenía 177 con contenido |

Tres cosas hay que decir, o es un cuento:

- **Ninguna se encontró *por* la proyección.** Estaban escritas, inyectadas y disponibles,
  y el trabajo las redescubrió midiendo. Una conjetura que nadie resuelve no es memoria:
  es una nota. Ese agujero es el que tantea
  [`experimentos/preguntar.py`](../experimentos/preguntar.py).
- **El puntaje dejó de escribirse a mano.** Vivía en prosa, en dos idiomas, y se
  desincronizó: esta sección llegó a decir *«seis proyecciones: dos confirmadas, dos
  refutadas, dos abiertas»* y dos de esas cuentas no existían. Ahora lo calcula el store:
  ```sh
  nightshift resolve      # las conjeturas abiertas, y la tasa de acierto
  ```
  Al 2026-08-28: **23 proyectadas · 15 abiertas · 5 confirmadas · 3 refutadas — 62% sobre
  8 resueltas.** No copies ese número a ningún lado: corré el comando.
- **El mismo trabajo encontró tres defectos en el brazo del tratamiento.** Los tres eran
  invisibles porque todos los hooks salen 0 por diseño. Están arreglados; lo que importa es
  por qué pasaron semanas sin que nada los dijera.

## La segunda noche, y lo único que se puede afirmar de ella

El 2026-08-28 el plugin consolidó su propio desarrollo dos veces, y los dos resultados no
fueron la misma clase de cosa. Esa diferencia es la observación más interesante que produjo
este proyecto, y también la más fácil de agrandar de más, así que va en su tamaño real.

**La primera candidata describió un mecanismo que no existe.** Abstrajo un bug de una
línea —un `or` que descartaba un marcador— como *«una propiedad derivada viaja como bandera
efímera que no cruza el sellado»*, con diagrama, analogía y cinco precondiciones
coherentes. No lo había alucinado: levantó el razonamiento ya escrito en los **comentarios
del propio código** —*«sin bandera de por medio»*, *«el comando está redactado, y eso no lo
afecta»*— y lo presentó como su diagnóstico de un bug del que esos comentarios no hablaban.

**La segunda no.** Su patrón —*«el trabajo cierra en verde porque el gate automatizado pasa,
pero cada fallo real ocurre fuera de él, en comandos improvisados: un nombre acuñado en la
intención viaja como puro texto y sólo revienta en la primera etapa que lo resuelve contra
algo real»*— describe bien lo que efectivamente pasó. Cuatro de sus cinco señales son
observaciones verificables de esa sesión: el gate en verde mientras los one-liners
improvisados fallaban, un traceback por argumentos armados a mano, un error de parseo del
shell, una trayectoria abierta con señal `unknown`. La quinta, un push rechazado por
refspec, **no se pudo confirmar** — puede ser una conflación. Cuatro de cinco, y la quinta
nombrada.

Y produjo el primer **contraste** del store ([ADR-005](adr/ADR-005-contraste-entre-implementaciones.md)):
la alternativa descartada conservada con la precondición bajo la cual seguía siendo la
correcta. Su campo `cost` nombra un precio real del cambio de ese día que nadie había
escrito — *«corregir la definición reescribe retroactivamente lo que las trayectorias
viejas significaban, y no queda registro de que significaban otra cosa»*.

### Qué cambió en el medio, y cuánto vale eso

Entre las dos corridas entraron dos cosas que apuntan exactamente al primer fallo: los
pasos que **leen el repositorio** (`grep`, `cat`, `git log`) ahora llegan al modelo
etiquetados `LECTURA-DEL-REPO` —contexto, nunca evidencia— y la hipótesis tiene que citar
un paso que **observe** algo, o quedarse en `null`. Medido sobre el store real: el **50% y
el 67%** de los pasos de esas trayectorias eran el repositorio leyéndose a sí mismo, y
llegaban con el mismo rango que un fallo.

**Y eso es una corrida contra una corrida, sobre corpus distintos, en sesiones distintas.**
No es evidencia de que el arreglo haya funcionado. Es la primera observación compatible con
que haya funcionado, y la diferencia entre esas dos frases es toda la disciplina de este
repositorio.

Corrélo para adelante vos:

```sh
nightshift why 07695a69     # la cadena, el dibujo, el contraste, lo que dice git
nightshift resolve          # las conjeturas que dejó abiertas
```

## El defecto que apareció cuando alguien midió la promesa

El README de arriba promete que cuando *describís lo que te está pasando*, la memoria
vuelve. Nadie lo había medido. Medido sobre el store real: **enganchaba 1 paráfrasis de
6.** El mecanismo que este proyecto más publicita —que la memoria se enganche con un
problema antes de que su síntoma se haya visto una vez— sólo disparaba si usabas las
palabras del propio modelo.

La causa era un piso único para dos clases de texto que no se parecen: una oración que el
modelo destiló no tiene relleno, así que una palabra de contenido ya es señal; un volcado
de error es casi todo andamiaje del harness. Partido en dos, más una regla de que ninguna
coincidencia puede apoyarse sólo en palabras que dicen *que* algo se rompió y no *qué*:
**4 de 6**, con el control negativo en cero las dos veces.

La historia desde entonces, cada paso medido: el piso subió a 2 en todas las superficies
y la compuerta del clasificador dejó de bloquear la inyección (enmienda 0.3.10 — decisión
de Matías), el plural regular se pliega a forma canónica (0.3.11), y los dos casos que
quedaban —`resumen`/`memoria consolidada`, `métrica`/`contador de cobertura`, que no
comparten una sola palabra— tienen un **fallback semántico** (ADR-003, enmendado el
2026-08-29). Es un *comando*, no un servicio: `embedding_command` lee textos por stdin y
escribe vectores por stdout, la red la habla el script del usuario
(`tools/embed-ollama.sh` envuelve al ollama local), y `nightshift/` sigue sin importar un
solo módulo de red. Calibrado contra `embeddinggemma` real antes de escribir el código:
los dos pares de sinónimos documentados dan 0.48 y 0.44 de coseno contra un máximo de
0.33 en pares ajenos. Lo que **no** hace, medido y escrito: unir un síntoma con un
mecanismo abstracto (0.24–0.28, *por debajo* de los ajenos). Resuelve sinónimos de
registro parecido, no comprensión. Apagado por defecto — sin el comando, el ranking es
letra por letra el léxico.

Reproducilo: `python3 experimentos/05-enganche-por-parafrasis.py --alternativas`
