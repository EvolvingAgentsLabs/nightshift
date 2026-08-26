# nightshift — reglas de trabajo

Este archivo es normativo para cualquier sesión de agente en este repositorio.
Fuente: `doc/PLAN-v0.3.md` §5.

## Antes de tocar nada

Leé, en este orden: `doc/PLAN-v0.3.md` (alcance de referencia) → `doc/00-spec.md`
(spec v0.3) → los dos ADRs → `LATER.md`.

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
- Agregar dependencias de API remota. Todo el modelo corre local.
- Empezar M5 (verify) antes del veredicto de M4.
- Abrir el adapter de OpenCode.
- Presentar nightshift como reemplazo, mejora o parche de Auto Memory, en cualquier
  texto del proyecto (ADR-001).
- Añadir features que no estén en el plan. Si parece buena idea, va a `LATER.md`.

## Límites del milestone actual (M0 — sólo documentación)

Mientras M0 esté abierto: **no hay código Python, no se tocan hooks, no se agregan
dependencias.** El linter lo verifica (`make lint-docs`) y falla si aparece un `.py`,
un `pyproject.toml` o un `requirements.txt`.

## Gate

```sh
make check
```

`lint-docs` comprueba estructura, enlaces internos y los límites de M0.
`validate-schema` comprueba que los ejemplos válidos validan y **que los inválidos son
rechazados** — un inválido que empieza a validar es un agujero en el esquema y rompe el
gate igual.

## Verificación de la doc del harness

Los nombres de hooks y el formato de salida de Claude Code **cambian entre versiones**.
Se verificaron el **2026-08-26** contra `https://code.claude.com/docs/en/hooks`.
Cualquier milestone que toque hooks los re-verifica primero y deja la fecha en
`doc/00-spec.md` §5.4.
