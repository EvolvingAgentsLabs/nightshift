# Plan — de acá al veredicto de M4

| Campo | Valor |
|---|---|
| Escrito | 2026-08-26 |
| Reemplaza | nada. Complementa `PLAN-v0.3.md` (alcance) y `HANDOFF.md` (cola) |
| Alcance | desde el estado de hoy hasta que M4 diga go o no-go, y qué pasa después |

## 0. El objetivo, dicho sin adornos

nightshift existe para responder **una** pregunta: ¿recordar *cómo se averiguó* algo
mejora el trabajo de un agente que ya tiene memoria declarativa nativa?

M4 la responde. Si la respuesta es no, el proyecto se congela como spec, y eso es un
resultado publicable — no un fracaso (spec §11). Todo lo demás de este plan son medios.

**El código dejó de ser el cuello de botella.** Lo que falta para llegar al veredicto son
decisiones humanas y evidencia de calendario.

## 1. Estado real, por milestone

| M | Código | Evidencia / gate | Qué falta |
|---|---|---|---|
| M0 | ✅ docs, schema, ADRs | ❌ **revisión de ADR-001 por Ismael** | 4 preguntas escritas al final del ADR |
| M1 | ✅ captura, redactor, `audit` | ⚠️ **1 de 5** sesiones con contenido capturado | usar el plugin |
| M2 | ✅ retrieval en dos pasadas, `why` | ✅ `why` reconstruye el origen | — |
| M3 | ✅ dream fase 1, scheduler | ⚠️ 0 de 3 noches | el timer ya corre solo |
| M4 | ✅ runner, 3 fixtures, adaptador | ❌ **PREREG en borrador, 20 `TODO(Matias)`** | congelarlo y correr |
| M5 | — | 🚫 bloqueado hasta el veredicto de M4 | — |

Los 186 tests, `make check`, `make bench-fixtures`, `make dream-selftest`,
`bench selftest` y `simulate` pasan. **No queda código en el camino de M4.**

## 2. El camino crítico, y su orden

El orden importa y no es el obvio:

```
ADR-001 (Ismael)  ──►  congelar PREREG (Matías)  ──►  correr M4  ──►  veredicto
      │                                                   ▲
      │                        5 sesiones reales ─────────┤
      └── decide qué capacidades son reales                │
          y por lo tanto qué mide el benchmark   3 noches ─┘
```

**Por qué ADR-001 va primero.** Ese ADR decide cuáles de las cinco capacidades son
"imposibles por diseño para el nativo" y cuáles son "todavía no lo hicieron". El
benchmark mide A, C y D. Si la revisión tumba una fila, el pre-registro que se congele
después mediría algo que ya no está en el roadmap — y un pre-registro congelado no se
re-abre sin quedar registrado como enmienda.

## 3. Fase 0 — las decisiones (no las puede tomar un agente)

### 0.1 Revisión de ADR-001

Las cuatro preguntas ya están escritas al final de
[`adr/ADR-001-no-competir-con-auto-dream.md`](adr/ADR-001-no-competir-con-auto-dream.md).
La que más pesa es la primera: si alguna capacidad es "todavía no lo hicieron", sale del
roadmap ahora, no en M4.

**Gate:** la respuesta escrita en el ADR, con fecha. Si cambia una fila de la matriz,
`LATER.md` gana un ítem con qué código sobra.

### 0.2 Congelar `bench/PREREG.md`

`nightshift bench check` lista los 20 con sección y línea. Agrupados por lo que
desbloquean:

| Bloque | Líneas de PREREG | Qué bloquea | Datos que ya existen para decidir |
|---|---|---|---|
| Constantes de corrida | 64–69: los **dos** modelos (agente y consolidación), seed, límite de tool calls, wall-clock | el adaptador se niega a correr sin el del agente, el límite y el reset | el smoke real midió **10–15 tool calls** y **27–52 s** por tarea |
| Umbrales por familia | 71, 72, 89, 90, 109 | el veredicto: sin ellos es *indecidible*, y eso nunca es go | — |
| Tolerancia de regresión | 35 | la mitad "cero regresión" de la regla de §1, que hoy no se evalúa | — |
| Fase de aprendizaje de A | 62 | cuántas de las 10 tareas enseñan y cuántas miden | el fixture propone 4 |
| Identificadores de fixtures | 74, 92 | congelar qué repos son | están construidos y verificados (`make bench-fixtures`) |
| Estadística y amenazas | 121, 122, 129, 131 | la validez de lo que se publique | ver §5 de este plan |

**Regla que no se toca:** Claude Code lee este archivo, no lo completa. Los números son de
Matías. Los datos de la columna derecha son mediciones, no propuestas.

**Gate:** `nightshift bench check` sale 0.

## 4. Fase 1 — la evidencia que sólo necesita calendario

Corre en paralelo con la fase 0. No hace falta esperar nada para empezar.

### 1.1 Cinco sesiones reales (gate de M1)

```sh
nightshift audit --min-sessions 5
```

**El gate cuenta sesiones que capturaron contenido, no sesiones a secas.** Una sesión
cuyos pasos están vacíos no prueba ausencia de fuga: no se puede filtrar lo que nunca se
guardó, y auditarla da un verde vacío. `audit` lo reporta separado y las huecas no suman.

Hoy van **1 de 5**: la sesión que construyó todo esto, que capturó 65 pasos con contenido
después del fix del 2026-08-26 (spec §5.9). Las dos anteriores son cascarón.

Mientras tanto, dos números a mirar en cada sesión:

```sh
nightshift status     # calidad de captura: cuántos pasos sin contenido
nightshift doctor     # falla si la captura de ahora llega vacía
```

### 1.2 Tres noches seguidas (gate operativo de M3)

El timer ya está instalado y corre a las 03:30.

```sh
nightshift schedule status    # las últimas corridas y su resultado
```

**Una precaución concreta:** dream consolida las trayectorias `closed` del período, y las
viejas son cascarón. Hasta que el store tenga volumen nuevo, conviene correrlo con una
ventana que no las alcance:

```sh
nightshift dream --lookback-days 3
```

Consolidar cáscaras produce candidatas vacías, y una candidata vacía se inyecta igual.

## 4.5 Fase 1.5 — el ensayo sellado

Antes de congelar nada, conviene saber si la máquina corre entera y cuánto cuesta. Y
saberlo **sin ver el efecto**, porque quien fija los umbrales no puede haberlo visto.

```sh
nightshift bench rehearse --fixture bench/fixtures/familia-d/fixture.json \
  --agent "python3 {agentes}/correr-agente.py {row} {prompt}" --repeats 1
```

`rehearse` corre con el pre-registro abierto —`run` se niega, y son cosas distintas— y
reporta **sólo salud**: cuántas celdas terminaron, cuánto tardaron, cuánto costaron,
cuántas produjeron dato medible, y cuáles fallaron y por qué. No dice si resolvieron, ni
en el reporte ni en la línea de progreso: sellar el final no serviría de nada si el
progreso lo va contando.

Los resultados quedan escritos y marcados como ensayo. `bench report --unseal` los
muestra y deja dicho que se los vio — si el pre-registro todavía no estaba congelado, eso
va a su registro de enmiendas.

**Lo que el primer ensayo encontró, antes de que existieran umbrales:**

| Hallazgo | Qué habría pasado sin el ensayo |
|---|---|
| **La familia C no cruzaba de repositorio**: sus dos repos vivían bajo un solo `git init` y el agente corría en la raíz | La familia de la capacidad C no ejercitaba la capacidad C |
| La segunda tarea de medición de C recibe la memoria de la primera, que es del mismo repo B | La mitad de la medición de C no sería cross-repo |
| La historia sembrada de la familia D usaba un fingerprint inventado, así que el retrieval la descartaba por "de otro repo" | La familia D habría medido precisión sobre **cero memorias inyectadas** |
| La fila S0 de la familia D no tiene inyecciones que clasificar | Ya estaba anotado; el ensayo lo confirmó con la corrida delante |
| Uso real | **~0,19 USD-lista por celda** con `sonnet` → ~20 las 102 celdas. Es la valorización a precio de lista que reporta el CLI (`costBasis: "list"`), útil para dimensionar la corrida; con una suscripción de Claude Code **no se factura eso**. Lo que se consume son tokens, y el ensayo los reporta. |

Ese primer dato es el tipo de cosa que sólo aparece corriendo, y es la cuarta amenaza a
la validez que no estaba en §5.

**Gate:** `bench rehearse` sale 0 sobre las tres familias.

## 5. Fase 2 — correr M4

### 2.0 Antes de arrancar

- [ ] `nightshift bench check` sale 0
- [ ] `make bench-fixtures` en verde
- [ ] las tres constantes exportadas (`NIGHTSHIFT_BENCH_MODEL`, `_TOOL_LIMIT`, `_RESET`)
- [ ] `NIGHTSHIFT_BENCH_UNATTENDED=1`, entendiendo qué significa (el agente corre sin
      pedir permisos, dentro de la copia desechable de cada celda)

### 2.1 El tamaño real de la corrida

| Familia | Tareas | Celdas (2 filas × 3 corridas) |
|---|---|---|
| A | 10 | 60 |
| C | 4 | 24 |
| D | 3 | 18 |
| **Total** | **17** | **102** |

Cada celda es **una sesión real de Claude Code**. Con los 27–52 s medidos en el smoke,
son ~1,1 h de reloj en serie, sin contar reintentos ni el dream entre corridas. El costo
en dólares no está medido todavía: ver §7.

### 2.2 Correr

```sh
for f in a c d; do
  nightshift bench run --fixture bench/fixtures/familia-$f/fixture.json \
    --agent "python3 {agentes}/correr-agente.py {row} {prompt}" \
    --repeats 3 --seed "$SEED_PREREGISTRADO"
done
nightshift bench report
```

**Por lote, sin mirar resultados parciales** (PREREG §5). Y si el resultado no llega al
umbral, es no-go: no se re-corre buscando una configuración mejor (PREREG regla 4).

### 2.3 El veredicto

`bench report` aplica la regla de §1 tal como está escrita y publica **todas** las
corridas, incluidas las que salieron mal. Tres salidas posibles, y la tercera es la que
más se olvida:

- **go** — mejora ≥ umbral en ≥2 de A/C/D.
- **no-go** — no.
- **indecidible** — falta un umbral o falta el dato de una familia. No es no-go, y sobre
  todo **no es go**.

## 6. Fase 3 — después del veredicto

### Si es go: M5 (`verify`)

Recién ahí se desbloquea. Lo que ya está decidido y no hay que re-discutir: qué cuenta
como reproducción está en [`adr/ADR-002-verify-gate.md`](adr/ADR-002-verify-gate.md), y
el esqueleto en spec §6.2 — worktree efímero en el `base_commit`, re-ejecución, gate del
usuario, `verified = {gate_id, passed_at, run_id}`, destruir el worktree pase lo que pase.

Lo que M5 tiene que resolver y todavía no está: cómo se declara un `gate_id` (registro y
formato), el presupuesto de verify por noche, y la caducidad de un `procedure` cuando el
repo avanza. Los tres están en `LATER.md`.

Su gate propio: la precisión de `procedure` tiene que superar a la de `candidate` en una
re-corrida del benchmark. Si verificar no separa mejor que no verificar, verificar no
sirve.

### Si es no-go: congelar como spec

Publicar la spec y el benchmark negativo. Es un resultado: dice que la memoria
procedimental cruda no le gana a la declarativa nativa **en estas tres familias, con este
modelo, con estos umbrales**, y deja el experimento reproducible para quien quiera
discutirlo.

Lo que no se hace: bajar los umbrales, agregar familias hasta que alguna dé, o cambiar el
baseline. Eso convierte un resultado en una anécdota.

## 7. Riesgos, con lo que se sabe de cada uno

| Riesgo | Evidencia | Mitigación |
|---|---|---|
| **Las amenazas de PREREG §5 están incompletas** | aparecieron **tres** que no estaban en §5: store por celda, ruta por tarea, y `cross_repo` apagado en la familia C — las tres medían cero o daban ventaja **por construcción** | releer §5 antes de congelar, sabiendo que la lista se demostró incompleta tres veces |
| **La familia C no puede medir con la config por defecto** | `cross_repo: false` deja a la fila S1 con **cero memorias** en el repo B. Medido: 0 candidatas con el default, 1 con el flag encendido | el valor de `cross_repo` para S1 es una constante del experimento y **no está en PREREG §2**. Agregarla y decidirla antes de congelar |
| ~~El benchmark tiene dos modelos y PREREG uno~~ | ADR-003: dream consolida con Claude Code, no con Qwen local | **resuelto**: PREREG §2 los pide por separado, y los dos siguen sin fijar. El de consolidación interviene sólo en S1 |
| **Lo redactado sale de la máquina** | consecuencia directa de ADR-003 | el backend `local` sigue a una línea de config para repos cuyo material no puede salir |
| **El store viejo es 82% cascarón** | `nightshift status` lo reporta | contar M1 desde el fix; correr dream con ventana corta |
| **El límite de tool calls no se puede imponer** | el CLI no expone `--max-turns` (verificado 2026-08-26) | PREREG tiene que decir qué se hace con una celda que lo excede: el adaptador la marca, no la corta |
| **Costo en dólares sin medir** | el adaptador emite `cost_usd` y ahora el runner lo guarda | **resuelto**: el reporte suma costo por celda y total. Falta la corrida real para tener el número |
| **Un solo `task_type` por sesión** | esta sesión cruzó implementar, analizar y depurar, y quedó `general` | afecta el uso real, no el benchmark (las tareas fixture son de un solo tipo) |

## 8. Lo que se puede construir mientras tanto

Corto, y ninguno bloquea a nadie:

1. ~~Guardar todas las métricas del adaptador~~ — **hecho**. El registro de cada celda
   guarda `tool_calls`, `num_turns`, `cost_usd`, `tool_limit_exceeded` y el id de sesión
   del agente, y el reporte suma el costo por celda y total.
2. ~~Verificar las formas de `tool_response`~~ — **hecho para siete tools** (Read, Bash,
   Write, Edit, Glob, Grep, ToolSearch), sondeadas de verdad. Encontró que `Edit`
   resumía el texto que **borraba**. Falta MCP: para eso sigue el fallback.
3. ~~`bench plan --json`~~ — **hecho**: `nightshift bench plan --json` da el tamaño de la
   grilla por familia y el total, con los bloqueos del pre-registro.

Lo que **no** se construye: política de retención del store (necesita volumen real),
encender la transferencia cross-repo (es una constante del experimento: va al pre-registro, no a un commit), y nada de M5.

## 9. Cómo se sabe que cada fase terminó

| Fase | Termina cuando |
|---|---|
| 0 | ADR-001 respondido con fecha **y** `nightshift bench check` sale 0 |
| 1.5 | `nightshift bench rehearse` sale 0 sobre las tres familias, sin desellar nada |
| 1 | `nightshift audit --min-sessions 5` sale 0 **y** `schedule status` muestra 3 noches seguidas sin intervención |
| 2 | `nightshift bench report` imprime un veredicto que no es "indecidible" |
| 3 | M5 arrancado, o la spec congelada y publicada |
