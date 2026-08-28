# Conjuntos retenidos — escritos por una persona, antes de medir

Un conjunto retenido son **síntomas dichos con palabras humanas** que el sistema no vio, y
sirve para una sola cosa: medir si una conjetura llega el día que hace falta.

## Por qué esta carpeta existe

El primer conjunto retenido —los tres síntomas de `cbbd7ff0`— **ya se gastó**. Se usó para
diagnosticar (`09`), para comparar brazos (`07`, H17) y para escribir dos reglas nuevas de
`dream.PROMPT`. Medir el prompt nuevo contra él sería entrenar contra el test, y el número
que saldría no valdría nada.

Hace falta uno nuevo, y **no lo puede escribir quien mide**. Si las paráfrasis las escribe
el mismo que escribió el prompt, lo único que se mide es cuánto se parece a sí mismo.

## El protocolo

1. Se elige una trayectoria consolidada que **no participó** de ningún experimento.
2. Se le muestran a una persona **sólo sus conjeturas** — no el patrón, no los pasos, no el
   diagrama.
3. Esa persona escribe, con sus palabras, cómo describiría cada síntoma **si le estuviera
   pasando**: como lo escribiría al abrir una sesión, no como lo escribiría un modelo.
4. Recién ahí se mide, con `12-sensibilidad.py`.

**La regla que hace que valga:** no releer la conjetura mientras se escribe. Copiar sus
sustantivos convierte la medición en una tautología. Si al terminar la paráfrasis comparte
media oración con la conjetura, está mal escrita.

## Estado

| Conjunto | Trayectoria | Quién lo escribe | Estado |
|---|---|---|---|
| `cbbd7ff0` | `implement_feature`, 2026-08-27 | Matías, en la sesión del 2026-08-28 | **gastado** — se usó para diagnosticar |
| `5b3ff97f` | `debug_test_failure`, 2026-08-27 | Matías | **pendiente** — `PENDIENTE-5b3ff97f.md` |

**Y desde el 2026-08-28 hace falta uno más, por el mismo motivo.** ADR-007 agrega un
segundo medio de ideación —la escena física— y su prompt lo escribió alguien que había
leído los tres síntomas de `cbbd7ff0` ese mismo día. Medir el brazo nuevo contra ellos
sería entrenar contra el test dos veces: el conjunto ya estaba gastado **y** el prompt se
escribió mirándolo. Por eso H23 está `BLOCKED` y no `FAIL`.
