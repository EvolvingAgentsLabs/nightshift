# Retenido pendiente — trayectoria `5b3ff97f` — la versión HUMANA sigue faltando

**Para Matías.** El 2026-08-28 autorizaste al agente a escribir él mismo las paráfrasis, y
están en [`5b3ff97f.md`](5b3ff97f.md) — **etiquetadas como techo de autor**: el mismo
agente escribió el retrieval, los prompts y el instrumento, así que ese archivo mide
cuánto se parece el sistema a sí mismo, no si la conjetura llega cuando a una persona le
pasa el síntoma.

**Este archivo queda como el lugar de la versión humana, que sigue haciendo falta.** El
protocolo es el de siempre ([`README.md`](README.md)): leé cada conjetura de
`5b3ff97f.md` (las citas con `>`), mirá para otro lado, y escribí en una línea cómo
describirías ese síntoma si te estuviera pasando — sin releer la conjetura y **sin leer
las frases que puso el agente**, que ahora también contaminan.

Cuando esté escrito: reemplazá las frases de `5b3ff97f.md` por las tuyas (o pedile al
agente que lo haga con tu texto), anotá en ese archivo que la procedencia pasó a ser
humana, y volvé a correr `python3 experimentos/12-sensibilidad.py`. Recién ese número es
sensibilidad.

---

## 2026-08-30 — el intento se abortó, y el motivo es el propio plugin

Matías pidió que el agente escribiera el retenido «derivado de la trayectoria cruda, sin
sesgo de autor». El intento se abortó **antes de escribir una sola frase**, y no por la
regla: por un hecho.

A las 19:16:30 y otra vez a las 19:21:10 de esa sesión, `retrieve` inyectó `5b3ff97f` en
rango 2 y 3 —enganchando por `signal_match,precondition_match,projected_match`— y con la
fila entera: patrón, señal decisiva, las tres precondiciones, el diagrama Mermaid y **los
tres síntomas proyectados**. Están en el registro de inyecciones del store y en el
`additionalContext` que quedó persistido.

Es exactamente el material que el protocolo de [`README.md`](README.md) prohíbe leer antes
de escribir. Escribir el retenido después de eso no habría sido un techo de autor: habría
sido una paráfrasis de un texto leído cinco minutos antes, con un número que parece
sensibilidad y no lo es.

**Lo que hace falta para el próximo intento, y ahora se sabe:**

1. Que lo escriba **una persona** — sigue siendo lo único que convierte este archivo en
   sensibilidad.
2. O, como mínimo, una sesión de sala limpia: el agente no puede haber recibido esa
   trayectoria por inyección. Hoy no hay forma de pedirle al retrieval que excluya una
   fila, y esa es la carencia concreta que este intento encontró.

**Y el hallazgo general, que vale más que el intento:** cuando el agente es a la vez el
experimentador y el sujeto, **su propia memoria procedimental es un contaminante
experimental**. El bucle de dogfooding no es neutral respecto de lo que mide.

