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
| M1 | ✅ captura, redactor, `audit` | ⚠️ 0 de 5 sesiones **desde el fix** | usar el plugin |
| M2 | ✅ retrieval en dos pasadas, `why` | ✅ `why` reconstruye el origen | — |
| M3 | ✅ dream fase 1, scheduler | ⚠️ 0 de 3 noches | el timer ya corre solo |
| M4 | ✅ runner, 3 fixtures, adaptador | ❌ **PREREG en borrador, 19 `TODO(Matias)`** | congelarlo y correr |
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

`nightshift bench check` lista los 19 con sección y línea. Agrupados por lo que
desbloquean:

| Bloque | Líneas de PREREG | Qué bloquea | Datos que ya existen para decidir |
|---|---|---|---|
| Constantes de corrida | 51–54: modelo, seed, límite de tool calls, wall-clock | el adaptador se niega a correr sin las tres primeras | el smoke real midió **10–15 tool calls** y **27–52 s** por tarea |
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

**El conteo arranca de cero hoy.** Las sesiones anteriores al 2026-08-26 se capturaron
con los campos del payload equivocados (spec §5.9): son cascarón, y `status` reporta que
el 82% del store no tiene contenido. Contarlas sería contar evidencia que no existe.

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
| **Las amenazas de PREREG §5 están incompletas** | corriendo el benchmark aparecieron dos que no estaban: store por celda (medía cero transferencia por construcción) y ruta por tarea (le daba ventaja a nightshift por construcción) | releer §5 antes de congelar, sabiendo que la lista se demostró incompleta |
| **La calidad de la abstracción del modelo no está medida** | dream corre con `qwen3.5:4b` y produce patrones genéricos; que sirvan lo dice M4 y nada más | fijar el modelo en PREREG; `qwen3.5:9b` está disponible local y no se probó |
| **El store viejo es 82% cascarón** | `nightshift status` lo reporta | contar M1 desde el fix; correr dream con ventana corta |
| **El límite de tool calls no se puede imponer** | el CLI no expone `--max-turns` (verificado 2026-08-26) | PREREG tiene que decir qué se hace con una celda que lo excede: el adaptador la marca, no la corta |
| **Costo en dólares sin medir** | el adaptador emite `cost_usd` y el runner **no lo guarda** | arreglarlo antes de correr M4 (§8) |
| **Un solo `task_type` por sesión** | esta sesión cruzó implementar, analizar y depurar, y quedó `general` | afecta el uso real, no el benchmark (las tareas fixture son de un solo tipo) |

## 8. Lo que se puede construir mientras tanto

Corto, y ninguno bloquea a nadie:

1. **Guardar todas las métricas del adaptador** en el registro de la corrida. Hoy el
   runner lee `tool_calls` y descarta `cost_usd`, `num_turns` y `tool_limit_exceeded`.
   Sin eso, el costo de M4 no queda medido y el límite de tool calls no queda auditable.
2. **Verificar las formas de `tool_response` de más tools**, sobre todo MCP. Hoy están
   verificadas Bash y Read; el resto usa un fallback que busca el primer valor con texto.
3. **`bench plan --json`** con el tamaño de la grilla, para estimar antes de correr.

Lo que **no** se construye: política de retención del store (necesita volumen real),
transferencia cross-repo encendida (decisión de producto), y nada de M5.

## 9. Cómo se sabe que cada fase terminó

| Fase | Termina cuando |
|---|---|
| 0 | ADR-001 respondido con fecha **y** `nightshift bench check` sale 0 |
| 1 | `nightshift audit --min-sessions 5` sale 0 **y** `schedule status` muestra 3 noches seguidas sin intervención |
| 2 | `nightshift bench report` imprime un veredicto que no es "indecidible" |
| 3 | M5 arrancado, o la spec congelada y publicada |
