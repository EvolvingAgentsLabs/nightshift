# Adaptador del agente

La pieza entre "el runner sabe qué correr" y "algo corre". `correr-agente.py` lanza
Claude Code sobre la tarea de una celda y emite las métricas que el runner sabe leer.

```sh
nightshift bench run --fixture bench/fixtures/familia-a/fixture.json \
  --agent "python3 ../../agentes/correr-agente.py {row} {prompt}"
```

## Se niega a correr, igual que el runner

Sin estas variables no arranca, y no elige valores por su cuenta:

| Variable | Qué es | Dónde se decide |
|---|---|---|
| `NIGHTSHIFT_BENCH_MODEL` | modelo exacto y versión | `TODO(Matias)` · PREREG §2 |
| `NIGHTSHIFT_BENCH_TOOL_LIMIT` | límite de tool calls por tarea | `TODO(Matias)` · PREREG §2 |
| `NIGHTSHIFT_BENCH_RESET` | comando de reset entre corridas | `TODO(Matias)` · PREREG §5 |
| `NIGHTSHIFT_BENCH_UNATTENDED=1` | aceptar que el agente corre sin pedir permisos | quien corre el benchmark |

Un script que elige el modelo por su cuenta está fijando la configuración del experimento
después de escribirlo, que es exactamente lo que el pre-registro existe para impedir.

## Las filas

- **S0** — Claude Code con Auto Memory y Auto Dream encendidos, **sin nightshift**. Es el
  baseline real (ADR-001): comparar contra un agente sin memoria sería comparar contra un
  rival que ya no existe.
- **S1** — lo mismo, más nightshift cargado con `--plugin-dir`, con `NIGHTSHIFT_HOME`
  apuntando a `.store/` dentro de la celda. Así cada celda arranca con la memoria que el
  fixture sembró y con ninguna otra.
- **S2** — se rechaza. Es de M5, y M5 está bloqueado hasta el veredicto de M4.

## Dos cosas verificadas contra el CLI el 2026-08-26

**Las tool calls se cuentan del stream.** `--output-format stream-json` emite un evento
`assistant` por mensaje, y los bloques `tool_use` de su contenido son las tool calls.
`num_turns` del resultado **no** es lo mismo — en la sonda dio 2 turnos para 1 tool call —
así que se reportan los dos por separado en vez de hacer pasar uno por el otro.

**El CLI no expone `--max-turns`.** El límite de tool calls de PREREG §2 no se puede
imponer: se mide y se reporta `tool_limit_exceeded`. Un límite que se declara y no se
aplica hay que decirlo, no suponerlo aplicado. Si en alguna versión aparece el flag, esto
es lo primero que hay que actualizar.

## Permisos

La corrida usa `--permission-mode bypassPermissions`, porque una corrida por lote que para
a pedir confirmación no termina nunca. Eso sólo es aceptable porque el agente trabaja
dentro de la **copia desechable de la celda** que arma el runner, nunca sobre el repo de
verdad. Por eso hay que aceptarlo explícitamente con `NIGHTSHIFT_BENCH_UNATTENDED=1`: es
una decisión de quien corre el benchmark, no un default.
