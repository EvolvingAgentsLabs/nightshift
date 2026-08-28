# ADR-007 — La escena antes del diagrama

| Campo | Valor |
|---|---|
| Estado | Aceptado — **como brazo, no como default**. Lo que decide cuál gana es una medición que todavía no se puede hacer (H23) |
| Fecha | 2026-08-28 |
| Reemplaza | nada. Agrega un segundo medio de ideación al que decidió [ADR-004](ADR-004-ideacion-y-proyeccion.md) |
| Relacionado | ADR-003 (el modelo corre por `subprocess`), ADR-004 (idear y proyectar), ADR-006 (el oráculo es un comando) |

## Contexto

ADR-004 decidió que dream **idea antes de abstraer**, y fijó el medio: un diagrama Mermaid.
Se aceptó con n=1 y lo dice en su propio texto.

El 2026-08-28 se corrió el control (`experimentos/07`, H17) contra un conjunto retenido que
ninguno de los dos brazos había visto:

| brazo | transferencia (3 retenidos) | control negativo (3 ajenos) |
|---|---|---|
| `observed` (sin idear) | 1 de 3 | 0 |
| `ideate` (Mermaid) | 2 de 3 | 1 |

Más superficie engancha más de las dos cosas. Mientras el control negativo no dé cero, la
transferencia extra no se puede separar de la indiscriminación — que es justo la separación
que la hipótesis pedía. **No refuta ADR-004: lo deja sin sostener**, y así quedó escrito.

La objeción que abre este ADR la trajo Matías, y es sobre el **medio**, no sobre idear:

> Un diagrama de cajas y flechas es **topología**, y para el modelo sigue siendo texto del
> mismo campo semántico que el código. Cuando una persona idea, no dibuja cajas: se imagina
> una escena, con mecánica y con física. Y cuando un idioma quiere comprimir un concepto
> entero en un signo, no escribe una oración: escribe un pictograma.

Las dos analogías que la sostienen —el chino escribiendo conceptos como logogramas, y los
esquemas de embeddings que fusionan varios vectores en uno solo— apuntan a lo mismo:
**comprimir a un signo obliga a quedarse con el invariante**, y una escena con mecánica
tiene restricciones que un flowchart no tiene. Qué empuja a qué, qué pesa, qué no entra por
dónde. Un flowchart admite cualquier cosa mientras las flechas cierren.

## Decisión

**Se agrega un segundo medio de ideación, `fisica`, y no se toca el default.**

1. `dream.MODOS_DE_IDEACION = ("mermaid", "fisica")`. `mermaid` sigue siendo el default.
   **Ningún modo apaga la ideación** (H14 sigue valiendo): `fisica` es otro dibujo, no una
   salida.
2. El brazo `fisica` pide, en este orden: **primero la escena** (`physical_scene`, una
   máquina o un sistema físico donde se ve dónde se pierde algo), **después el
   razonamiento** —explícitamente sobre la escena y no sobre el código— y de ahí las
   proyecciones, y **por último el logograma** (`logogram`), de dos a cuatro palabras que
   nombran el mecanismo entero. `diagram` va en null: en este modo el dibujo es la escena.
3. **Los dos campos tienen gate determinista**, y esto es lo que separa esto de un deseo
   escrito en un prompt (CLAUDE.md regla 2):
   - `validate_scene` rechaza una escena que **nombre el dominio del software** o que
     contenga identificadores de código. Sin ese gate, el modelo contesta con la
     explicación de siempre encabezada por «imaginá una máquina» y nada lo nota.
   - `validate_logogram` exige de dos a cuatro palabras, sin puntuación de oración y sin
     nombres de herramienta.
   - Un rechazo entra al **mismo bucle de reintentos** que una fuga.
4. **La escena y el logograma se muestran y NO se buscan.** No entran en la superficie de
   búsqueda (`signals`, `valid_when`, `projected_signals`, spec §5.10). Entran en el bloque
   que lee el agente: primero el signo, después la escena.
5. **Los dos brazos no acumulan.** En `fisica` el diagrama se descarta aunque el modelo lo
   devuelva. Si un brazo guardara los dos medios, la comparación sería entre acumular texto
   y no acumularlo — que es exactamente lo que H17 midió y castigó.
6. Se elige con `nightshift dream --ideacion fisica` (y `sleep`). El reporte de la corrida
   dice cuál corrió: `strategy: ideate:fisica`.

**Lo que este ADR NO decide, y es lo importante:** cuál de los dos medios es mejor. Cambiar
el default por decreto sería el mismo error que prender el primero con n=1, sólo que con
n=0. Lo decide H23, y H23 está `BLOCKED`.

## Consecuencias

- **H17 no se toca y sigue en `FAIL`.** Su veredicto es sobre el brazo Mermaid, que sí se
  midió. Convertir un `FAIL` en `BLOCKED` cambiando el instrumento sería lavar un
  resultado, y es peor que tenerlo en contra.
- **El conjunto retenido de `cbbd7ff0` no sirve para medir esto.** Se gastó diagnosticando,
  y el prompt de este brazo lo escribió alguien que lo había leído el mismo día. Medir
  contra él sería entrenar contra el test. Hace falta uno nuevo, escrito por una persona
  que sólo vio las conjeturas (`experimentos/retenido/README.md`).
- **El logograma no resuelve el problema de la sensibilidad, y no hay que venderlo así.**
  Contra una compresión de dos a cuatro palabras el enganche por palabras funciona **peor**
  que contra un síntoma, no mejor: `signals` está escrito con las palabras de quien sufre el
  problema y el logograma con las de quien lo entendió. Evocar un logograma desde el prompt
  —que es lo que haría falta para que ayude a encontrar— necesita embeddings, y eso choca
  con ADR-003. Por eso se muestra y no se busca.
- **Se toca una línea del prompt del brazo default.** La plantilla JSON compartida decía
  «diagrama Mermaid» y ahora dice «el dibujo del mecanismo, en el medio que te hayan pedido
  arriba». El brazo `mermaid` sigue pidiendo Mermaid, en su prefijo. Queda escrito porque un
  cambio silencioso en el brazo que se compara es el error que este repo ya documentó.
- **Cuesta.** Un medio nuevo son dos prompts que mantener y dos gates más que pueden gastar
  reintentos. `experimentos/14` mide cuántos.
- Ninguna dependencia nueva, ninguna API key, ninguna red. El modelo sigue corriendo por
  `subprocess` (ADR-003).

## Alternativas consideradas

- **Reemplazar Mermaid por la escena.** Es lo que pedía la propuesta original, y es lo que
  se hará si H23 sale a favor. Hacerlo hoy sería sacar un medio que pasa sus gates para
  poner otro que nadie midió: decidir por decreto lo mismo que ADR-004 decidió con n=1, con
  menos evidencia todavía.
- **Pedir la escena *además* del diagrama, en el mismo brazo.** Suma superficie, que es
  literalmente lo que H17 castigó, y vuelve la comparación imposible: no se sabría si mejoró
  el medio o si simplemente hay más texto.
- **Meter el logograma en la superficie de búsqueda.** Cambiaría el tratamiento del
  experimento sin dejar constancia (PREREG §2), y con el store creciendo el enganche ya
  discrimina **menos** (`experimentos/13`: con el piso de hoy, 17 de 24 prompts ajenos
  enganchan algo). Agregar una superficie corta y densa empeora esa mitad.
- **Embeddings para comparar prompt y logograma.** Es la forma correcta de «evocar» y no se
  puede: exige una dependencia de tercero o una API key, las dos prohibidas por ADR-003.
  Queda anotado en `LATER.md`, donde ya está el mismo choque por los sinónimos.
- **Un `--ideacion off`.** No existe y no va a existir: sería la clave de config que la
  enmienda 0.3.7 sacó, con otro nombre.
