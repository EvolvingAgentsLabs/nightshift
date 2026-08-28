# nightshift — reglas de trabajo

Este archivo es normativo para cualquier sesión de agente en este repositorio.
Fuente: `doc/PLAN-v0.3.md` §5.

## Antes de tocar nada

Leé, en este orden: **`doc/HANDOFF.md`** (estado real y cola de trabajo; empezá por
**§0-bis, el pivot**, que manda sobre `doc/PLAN-M4.md`) → `doc/PLAN-v0.3.md` (alcance de
referencia) → `doc/00-spec.md` (spec v0.3) → los ADRs → `LATER.md`.

## Reglas

1. **Un milestone por rama.** Nada de mezclar M1 y M2 en la misma rama.
2. **El gate es un script, no un juicio.** PR sólo si el gate pasa. Si el gate no se
   puede automatizar, no es un gate: es una opinión, y va al PR como comentario.
3. **Cada sesión termina en commit medible.** Si no hay commit, el motivo va a
   `LATER.md`. No hay tercera opción.
4. **Claude Code no fija umbrales de benchmark.** Los lee de `bench/PREREG.md`.
   Todo `TODO(Matias)` lo resuelve una persona. Completar uno es una violación, no
   una ayuda.
5. **Tests antes que código.** Gates antes que resultados.

## Prohibido

- Escribir en el directorio de Auto Memory (`~/.claude/projects/*/memory/`) o en
  cualquier ruta propiedad de la memoria nativa. Leer `MEMORY.md` está permitido, sólo
  como señal de retrieval.
- Agregar dependencias que exijan una **API key nueva**. El modelo que consolida corre
  en Claude Code o en Qwen local, los dos por `subprocess` (ADR-003). Ningún módulo de
  `nightshift/` habla por red: `make lint-code` lo verifica.
- Empezar M5 (verify). M4 quedó **pausado** por el pivot (HANDOFF §0-bis), así que el
  veredicto que lo desbloqueaba no va a llegar: lo que hoy lo prohíbe es que nada llega a
  `procedure` y que el dogfooding no lo desbloquea.
- Tratar M4 o el gate humano de M0 como **cerrados**. Están pausados, que es otra cosa:
  siguen sin respuesta y el proyecto no puede afirmar que la memoria procedimental sirve.
- Abrir el adapter de OpenCode.
- Presentar nightshift como reemplazo, mejora o parche de Auto Memory, en cualquier
  texto del proyecto (ADR-001).
- Añadir features que no estén en el plan. Si parece buena idea, va a `LATER.md`.

## Objetivo actual: las tres ideas (pivot del 2026-08-27)

CTE (la cadena de pensamiento es la de ejecución), correr la cadena **para adelante**
(proyectar síntomas que nadie vio), e **idear antes de razonar** (dibujar el mecanismo).
El detalle está en `doc/HANDOFF.md` §0-bis, que es normativo igual que este archivo.

El gate es **`make dogfood`**: `make check` y después `doctor`, `audit` y `status` sobre
el store **real**. Lo que ese gate **no** dice: que la memoria sirva. Eso lo iba a medir
M4 y no se midió.

`dream.consolidate` **idea siempre**: no hay clave de config que lo apague, y
`build_prompt(..., ideate=False)` existe sólo como brazo de control del experimento.

**Decidido por Matías el 2026-08-28 (enmienda 0.3.10, implementado):** la compuerta del
clasificador ya no bloquea la inyección —todos los prompts se evalúan, y las pasadas no
estructurales sólo inyectan lo que engancha—, el piso de discriminación es **2** en todas
las superficies, el **logograma** es superficie de búsqueda con prioridad de orden, y el
default de ideación es **`fisica`** (ADR-007, enmienda). Ninguna de las cuatro está
sostenida por una medición de beneficio: son decisiones del dueño del proyecto, y la spec
las registra con esa procedencia. Bajo el tratamiento nuevo H17 pasó a favor (2 de 3
contra 0, ajenos 0 — evidencia débil: su retenido está gastado), y el costo quedó medido
en H23 y H24, los dos en contra: con el piso en 2, la sensibilidad a la paráfrasis cayó a
0 de 5 sobre el retenido de `5b3ff97f`, y el techo a escala bajó de 6/6 a 3/6 — aunque lo
que sí engancha ahora **llega** (3/6 contra 0/6 con la compuerta vieja). El retenido de
`5b3ff97f` lo escribió el agente por autorización expresa: lo que mide es un techo de
autor, no sensibilidad.

## Milestone de referencia: M3 — dream `consolidate` + scheduler

**Este repositorio es el plugin.** Si la sesión se abrió con `claude --plugin-dir .`, los
hooks que están capturando esta misma sesión son el código de este working tree. Editar
`nightshift/hook.py` cambia cómo se captura la próxima tool call.

Empezá cualquier sesión de desarrollo con:

```sh
nightshift dev      # o ./bin/nightshift dev
```

### El loop cuando tocás código del plugin

1. Cambiás el código.
2. `make check` — lint-docs, lint-code, esquema, tests y el replay end-to-end. Todo, no
   la parte que creés haber tocado.
3. `/reload-plugins` **sólo si tocaste `hooks/hooks.json`, una skill o el manifiesto.**
   Los cambios en `nightshift/*.py` aplican en el próximo evento de hook, porque cada
   hook corre un proceso nuevo.
4. `nightshift selftest` desde la sesión recargada.
5. Commit. Si no hay nada que commitear, el motivo va a `LATER.md`.

### Invariantes que el linter defiende (no son estilo)

- **Sólo librería estándar.** Ningún import de tercero, en `nightshift/` ni en `tests/`.
- **Sin red.** Ningún `socket`, `urllib`, `http`, `requests` en `nightshift/`.
- **Coexistencia.** Sólo `config.py` (el guard), `context.py` (lectura de señal) y
  `cli.py` (el doctor, que afirma que el guard rechaza) pueden nombrar
  `~/.claude/projects/*/memory/`. Cualquier otro archivo es una vía de escritura sin
  auditar.
- **Los hooks no ensucian stdout.** Lo que sale de un hook es JSON válido o nada.
- **`hook.main` sale 0 siempre.** Una sesión con nightshift roto debe ser
  indistinguible de una sesión sin nightshift (spec §7.2).

### Qué es real y qué no

Al describir el proyecto — en el README, en un commit, en una demo — esto es lo que
corresponde decir:

- **Hecho:** captura (7 hooks), redactor determinista, store SQLite, retrieval
  estructural e inyección, `why`, doctor, selftest, `audit` (el gate de M1), **dream
  fase 1 (`consolidate`)** con modelo local el **scheduler** (launchd/systemd/loop) con
  registro de corridas, el **runner del benchmark de M4** — que se niega a correr
  porque el pre-registro no está congelado — y un **ensayo end-to-end**
  (`nightshift simulate`) que corre la máquina entera con sesiones sintéticas.
- **No construido:** dream fase 2 (`verify`). El benchmark tiene runner pero **no tiene
  resultados**: no corrió nunca y no puede correr hasta que Matías congele `PREREG`. Hay `candidate`, pero
  **nada llega a `procedure`**: ninguna memoria inyectada está verificada. Una
  `candidate` la abstrajo un modelo local y nadie la reprodujo contra un gate. No la
  describas como si lo estuviera.
- **No decidido:** todos los `TODO(Matias)` de `bench/PREREG.md`, y el gate humano de M0
  (la revisión de ADR-001 por Ismael), que sigue pendiente.

**Un ensayo no es evidencia.** `nightshift simulate` corre sesiones sintéticas y noches
simuladas; el gate de M1 pide 5 sesiones **reales** y el de M3, tres **noches** reales.
Reportar un ensayo como gate cerrado es fabricar evidencia, y está prohibido igual que
completar un `TODO(Matias)`.

## Verificación de la doc del harness

Los nombres de hooks y el formato de salida de Claude Code **cambian entre versiones**.
Se verificaron el **2026-08-26** contra `https://code.claude.com/docs/en/hooks`, y los
**nombres de campo del payload** se sondearon el mismo día ejecutando los hooks de verdad
(spec §5.9). Cualquier milestone que toque hooks los re-verifica primero y deja la fecha
en `doc/00-spec.md` §5.4.

**Leer la doc no alcanza, y esto costó dos milestones:** M1 y M2 se implementaron leyendo
`user_input`, `tool_output` y `error_message`, que no existen — los campos reales son
`prompt`, `tool_response` y `error`. La captura guardó estructura vacía durante todo ese
tiempo sin fallar nunca, porque los hooks salen 0 pase lo que pase. Si tocás la captura:
sondeá el payload real, no confíes en el replay del selftest — que también estaba escrito
con las claves inventadas y por eso pasaba en verde.
