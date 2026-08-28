---
description: Resolve a conjecture that dream projected — confirmed or refuted, always with evidence. Use when the user asks about projections, wants to record that a projected symptom happened or cannot happen, or asks for the conjecture hit rate.
disable-model-invocation: true
---

# /nightshift:resolve

Dream proyecta síntomas que **nadie observó**. Este comando es el otro extremo de eso:
decirle al store que uno pasó, o que no puede pasar.

Sin esto, una conjetura queda abierta para siempre y sigue enganchando igual. **Una
conjetura que nadie resuelve no es memoria, es una nota.**

Listá lo que hay para resolver y reportá la salida:

```sh
nightshift resolve
```

Si `nightshift` no está en el `PATH`, usá `"${CLAUDE_PLUGIN_ROOT}/bin/nightshift" resolve`.

Para resolver una, con su id:

```sh
nightshift resolve <id> --confirmed --evidence "lo vi pasar en …"
nightshift resolve <id> --refuted   --evidence "no puede pasar porque …"
```

Argumentos útiles: `--by "quién"` (default `human`), `--all` para ver también las
resueltas, `--json`.

## Reglas que el comando defiende, y que conviene explicarle al usuario

- **La evidencia es obligatoria en los dos sentidos.** Refutar sin motivo es olvidar con
  otro nombre; confirmar sin motivo es una explicación plausible anotada como hallazgo,
  que es justo el tipo de memoria que este proyecto dice no querer.
- **No hay un estado tibio.** `confirmed` o `refuted`. El valor de esto es que obliga a
  decidir; lo que todavía no se sabe se queda `open`, que ya es un estado.
- **Una refutada deja de engancharse** con cualquier prompt, y **no se borra**:
  `/nightshift:why <trayectoria>` la sigue mostrando con su motivo.
- **Una confirmada NO asciende.** Sigue pesando la mitad que una señal observada y se
  anuncia aparte. Que el mecanismo haya acertado no vuelve a esta sesión la que lo
  observó, y borrar esa frontera borra ADR-004 entero.

## Qué no es

**No es `verify`.** Esto registra el juicio de una persona sobre una conjetura; `verify`
(M5, ADR-002) reproduce una trayectoria contra un gate automático. Una conjetura
confirmada no vuelve verificada a la memoria que la produjo, y nada llega a `procedure`.
