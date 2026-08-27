# Plan — de acá al veredicto de M4

| Campo | Valor |
|---|---|
| Escrito | 2026-08-26 |
| Reordenado | 2026-08-27, después de encontrar tres defectos en el brazo S1 (§2.5) |
| Reemplaza | nada. Complementa `PLAN-v0.3.md` (alcance) y `HANDOFF.md` (cola) |
| Alcance | desde el estado de hoy hasta que M4 diga go o no-go, y qué pasa después |

## 0. El objetivo, dicho sin adornos

nightshift existe para responder **una** pregunta: ¿recordar *cómo se averiguó* algo
mejora el trabajo de un agente que ya tiene memoria declarativa nativa?

M4 la responde. Si la respuesta es no, el proyecto se congela como spec, y eso es un
resultado publicable — no un fracaso (spec §11). Todo lo demás de este plan son medios.

**Esto decía "el código dejó de ser el cuello de botella". El 2026-08-27 dejó de ser
cierto**, y conviene leer por qué antes de seguir: en una sola sesión, sin agregar una
sola feature, aparecieron **tres defectos en el brazo S1** —el tratamiento que M4 mide— y
los tres eran invisibles porque todo salía 0. Están en §2.5. Lo que falta para el
veredicto sigue siendo, en su mayor parte, decisiones humanas y calendario; pero congelar
un pre-registro sobre un tratamiento que nadie vio funcionar mide la plomería, no la
hipótesis.

## 1. Estado real, por milestone

| M | Código | Evidencia / gate | Qué falta |
|---|---|---|---|
| M0 | ✅ docs, schema, ADRs | ❌ **revisión de ADR-001 por Ismael** | 4 preguntas escritas al final del ADR |
| M1 | ✅ captura, redactor, `audit` | ⚠️ **1 de 5** sesiones con contenido capturado | usar el plugin |
| M2 | ✅ retrieval en dos pasadas, `why` | ✅ `why` reconstruye el origen | — |
| M3 | ✅ dream fase 1, scheduler | ⚠️ 0 de 3 noches | el timer ya corre solo |
| M4 | ✅ runner, 3 fixtures, adaptador | ❌ **PREREG en borrador, 21 `TODO(Matias)`** | congelarlo y correr |
| M5 | — | 🚫 bloqueado hasta el veredicto de M4 | — |

Los 280 tests, `make check`, `make bench-fixtures`, `bench selftest` y `simulate` pasan.
**`simulate` pasa con modelo desde el 2026-08-27**: antes salía en rojo por un problema
del ensayo y el rojo acusaba a dream (§2.5).

**Sí queda código en el camino de M4**, y es poco pero no es cosmético: lo que hace que
S1 sea S1. La lista, con su orden, está en §2.5.

## 2. El camino crítico, y su orden

El orden importa y no es el obvio. **Reordenado el 2026-08-27**; el anterior está al pie
de esta sección, tachado, porque el motivo del cambio vale más que el diagrama.

```
                     ┌── usar el plugin: 5 sesiones reales ──┐
                     │   (produce el material que encuentra  │
                     │    los defectos, no sólo el gate)     │
                     ▼                                       ▼
S1 es S1 (§2.5)  ──────────────────────────────────►  congelar PREREG  ──►  M4  ──► veredicto
      ▲                                                     ▲
      │                                    ADR-001 (Ismael) ┘
      └── los tres defectos de hoy, y lo que          3 noches ──────────┘
          queda: `decisive`, `valid_when`
```

**Qué cambió respecto del orden anterior.** Antes, "5 sesiones reales" y "3 noches" eran
evidencia *en paralelo*: gates que se cierran con calendario mientras las decisiones
avanzan. Hoy las cinco sesiones pasan a estar **en el camino**, por una razón empírica:
los tres defectos del brazo S1 que se encontraron el 2026-08-27 salieron de mirar un store
real de **cuatro** trayectorias. No salieron de leer el código, ni de los tests —que
estaban en verde— ni del ensayo —que estaba en rojo por otra cosa—. Con cinco sesiones hay
más material del que salió todo esto; con cero, no hay ninguno.

Dicho de otro modo: **el store real es el instrumento, y hasta ahora se lo trató como un
trámite.**

**Por qué ADR-001 sigue primero.** Sin cambios: ese ADR decide cuáles de las cinco
capacidades son "imposibles por diseño para el nativo" y cuáles son "todavía no lo
hicieron". El benchmark mide A, C y D. Si la revisión tumba una fila, el pre-registro que
se congele después mediría algo que ya no está en el roadmap — y un pre-registro congelado
no se re-abre sin quedar registrado como enmienda.

~~`ADR-001 → congelar PREREG → correr M4`, con las 5 sesiones y las 3 noches colgando en
paralelo.~~ El orden viejo suponía que el tratamiento estaba terminado. No lo estaba, y lo
que lo demostró fue mirar el store.

## 2.5 Fase 0.5 — que S1 sea S1

**El problema, en una línea:** el pre-registro se congela sobre un tratamiento, no sobre
un plan. Si S1 inyecta lo que no corresponde, o dream consolida sobre material vacío, M4
mide eso — y un no-go no se puede distinguir de un fallo de plomería. Es la primera
objeción que hizo la revisión externa: *descartá fallo de recall antes de descartar la
hipótesis*.

### Lo que se encontró el 2026-08-27, y el patrón que comparten

| # | Defecto | Cómo se veía |
|---|---|---|
| 1 | El retrieval de una trayectoria **cruda** no miraba el prompt: dos síntomas distintos daban el mismo orden y los mismos scores. Un síntoma **proyectado** por el modelo pesaba 0.75; un fallo **observado**, cero | inyecciones normales, `why` correcto |
| 2 | A dream le llegaban **seis líneas vacías** de una trayectoria de 400 pasos con 177 con contenido: la ventana se elegía por `decisive`, que marca el 38% de los pasos y no exige contenido | "sin patrón común": una respuesta legítima del modelo |
| 3 | El ensayo end-to-end le sacaba la **sesión al modelo** —reemplaza `HOME` para no instalar un timer de verdad— y reportaba el fallo como "dream no produjo ninguna candidata" | `make simulate` en rojo, acusando a dream |

Los tres son el mismo modo de falla que ya costó dos milestones: **nada falla.** Uno se
veía como una inyección normal, otro como una respuesta razonable del modelo, y el tercero
como un rojo que señalaba al inocente. Ninguno lo habría encontrado un test: los tests
estaban en verde y siguen estándolo.

Y hay un cuarto, más incómodo, que no es de código: **el diagnóstico anotado en
`LATER.md`** —"dream no consolida porque un día es un grupo de uno"— era plausible y era
falso. Sobrevivió un día porque sonaba bien. Una explicación plausible anotada como
hallazgo es exactamente el tipo de memoria que este proyecto dice no querer.

### Lo que queda, en orden

| Orden | Qué | Por qué acá | Gate |
|---|---|---|---|
| **P1** | La bandera `decisive` marca el 38% de los pasos porque mezcla diagnóstico (un fallo) con desenlace (un test que corrió) | Es el insumo de tres cosas a la vez: el peso `W_DECISIVE` del ranking —que se cobra casi siempre y por lo tanto no ordena—, `hook._infer_outcome` y la ventana que ve dream. Cambiarla después de congelar es enmendar el pre-registro | `make check`, y `status` reportando un porcentaje que discrimine |
| **P2** | `valid_when` se muestra y no se busca: las precondiciones no son clave de recuperación | Es la otra mitad del modelo mental —"esto ya lo vi" vs "esto aplica acá"— y va **sola** en su commit para que M4 pueda atribuir qué movió el ranking | test que falla si se revierte |
| **P3** | Por celda del benchmark: **qué** memorias se inyectaron y con qué motivo. Hoy se guarda el conteo (`injections`) y el resumen dice si el tratamiento se aplicó (`treated`) | No cambia el tratamiento: cambia si un no-go se puede leer. Con el conteo se distingue "S1 no participó" de "S1 perdió"; con el motivo se distingue además "recuperó lo que no era" | el reporte lo imprime |
| **P4** | La calidad de captura se promedia sobre cohortes distintas: `status` dice 52% de pasos vacíos y la última trayectoria va 1 de 52 (2%) | Una alarma que suena para siempre es donde se esconde la regresión siguiente | `status` distinguiendo cohortes |

**P1 y P2 cambian qué es S1: van antes de congelar. P3 y P4 no lo cambian: pueden entrar
hasta el día antes de correr.**

### La regla de corte — cuándo S1 está listo

Sin esto, "mejorar el tratamiento antes de medirlo" no termina nunca, que es su propio
riesgo. **S1 está listo cuando estas cuatro salen 0, y no cuando parezca bueno:**

```sh
make check                              # 280 tests, lint, esquema, selftest
make simulate                           # el ensayo entero, con modelo
nightshift audit --min-sessions 5       # 5 sesiones reales con contenido capturado
nightshift dream --lookback-days 7      # ≥1 candidata sobre material nuevo
```

Y una condición más, que hoy no tiene comando y por eso es una pregunta de §10: que la
inyección que recibe una sesión traiga un motivo que **no** sea sólo `same_repo` y
recencia. Todo lo que aparezca después de eso va a `LATER.md` y se decide con el veredicto
en la mano, no antes.

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

### 1.6 El presupuesto es tiempo, no dinero — decidido por Matías, 2026-08-27

Medido sobre las 39 celdas de los tres ensayos: mediana 37,8 s por celda, p90 70,5 s.
**Las 102 celdas entran en 1,1 h en serie; 2,0 h con el p90 y 2,8 h en el peor caso
observado.** M4 entero entra en una noche sin paralelismo y sin nadie mirando.

La factibilidad no es el cuello de botella. El pre-registro sí.

El runner lo defiende en vez de sólo documentarlo: `bench plan` proyecta las horas antes
de arrancar con datos medidos, `--budget-minutes` corta al terminar una repetición, y la
matriz pasó a ir **repetición → fila** para que cortar deje las dos filas con el mismo n.
Ver PREREG §2.1.

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

**Ojo con el título de esta sección.** Se escribió cuando se creía que no quedaba código
en el camino, y decía "ninguno bloquea a nadie". Desde §2.5 eso vale para lo de abajo,
que ya está hecho — no para P1 y P2, que **sí** bloquean el congelamiento.

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
| 0.5 | las cuatro de la regla de corte de §2.5 salen 0, con P1 y P2 mergeados |
| 0 | ADR-001 respondido con fecha **y** `nightshift bench check` sale 0 |
| 1.5 | `nightshift bench rehearse` sale 0 sobre las tres familias, sin desellar nada |
| 1 | `nightshift audit --min-sessions 5` sale 0 **y** `schedule status` muestra 3 noches seguidas sin intervención |
| 2 | `nightshift bench report` imprime un veredicto que no es "indecidible" |
| 3 | M5 arrancado, o la spec congelada y publicada |

## 10. Preguntas abiertas — para responder, o para descartar

Ninguna la puede cerrar un agente: o son decisiones, o cambian qué mide el experimento.
Están numeradas para poder contestarlas por número. **Descartar una es una respuesta**, y
si se descarta conviene escribir por qué acá mismo.

### Q1 — ¿La configuración de retrieval entra al pre-registro?

PREREG §2 fija el modelo del agente, el de consolidación y la `consolidation_strategy`
porque cambian **qué es** el brazo S1. `max_injected`, `cross_repo` y la función de
ranking (`retrieve.W_*`) deciden qué se inyecta, que es literalmente el tratamiento, y no
están pre-registrados. El 2026-08-27 el ranking cambió y nada en el pre-registro habría
dejado constancia.

*Qué desbloquea:* que dos corridas de S1 sean comparables entre sí.
*Por qué no lo escribo yo:* la regla 3 del pre-registro dice que Claude Code lee y no
propone. Si la respuesta es sí, el `TODO(Matias)` lo agrega una persona.

### Q2 — `decisive`: ¿se parte en dos banderas o se aprieta la heurística?

Hoy marca un fallo observado **y** cualquier comando de test que corrió: el 38% de los
pasos del store real. Dos caminos, y no son equivalentes:

- **Partirla** en `decisive` (diagnóstica) y algo como `outcome_signal` → toca
  `trajectory.v1`, y el esquema dice que un cambio incompatible crea `v2`, no edita `v1`.
- **Apretarla** → no toca el esquema, y deja `_infer_outcome` sin su insumo actual.

*Qué desbloquea:* P1 de §2.5, que es lo primero de la fase 0.5.

### Q3 — ¿Se congela el pre-registro antes o después de P1 y P2?

Es la pregunta del reorden, y la respuesta razonable puede ser "antes". Congelar antes
mide el tratamiento tal como está hoy —defensible, y más rápido— pero deja el no-go
ambiguo: no se podría distinguir "recordar cómo no sirve" de "recuperamos mal". Congelar
después atrasa, y tiene su propio riesgo: pulir el tratamiento hasta que dé.

La regla de corte de §2.5 existe para acotar ese segundo riesgo. Si aun así el atraso no
se justifica, **congelar ya es una respuesta válida** y este plan se reordena de nuevo.

### Q4 — ¿El plugin se instala en la sesión de trabajo diaria?

Constatado el 2026-08-27: nightshift **no** figura en `installed_plugins.json` y la sesión
no se abrió con `--plugin-dir`, así que las sesiones de desarrollo **no se están
capturando**. El gate de M1 (5 sesiones con contenido) no avanza solo, y las cinco
sesiones son ahora parte del camino crítico (§2).

*Qué desbloquea:* todo lo de la fase 0.5 que necesita material real.

### Q5 — ¿El contexto gastado entra como métrica?

El runner ya registra `input_tokens`, `output_tokens`, `tool_calls` y `num_turns` por
celda. Las métricas de PREREG §3 son tasa de resolución (primaria) y tool calls hasta el
fix (secundaria): **ninguna mira los tokens.** Una memoria que resuelve igual pero gasta
el doble de contexto hoy figura como empate.

*Qué desbloquea:* poder decir si la inyección se paga sola. Es un umbral: es de Matías.

### Q6 — Una noche que no consolida nada nuevo, ¿tiene que salir 1?

Medido en el ensayo: después de que dream consolida el período, las tres noches
siguientes salen **exit 1** —"había material y no salió ninguna candidata"— porque el
material que queda ya está consolidado. El gate de M3 son tres noches seguidas leídas con
`schedule status`, y así se leen tres rojos seguidos en una máquina sana.

*Opciones:* distinguir "no había nada nuevo" (0) de "había y falló" (1), o dejarlo y
documentar cómo se lee el gate.

### Q7 — ¿Qué se hace con las trayectorias cascarón del store real?

Las anteriores al arreglo de los campos del payload (2026-08-26) están vacías o casi. Hoy
dream ya no las manda al modelo (spec §6.1), pero siguen contando en el promedio de
calidad de captura y en el conteo del gate de M1. *Opciones:* marcarlas con una cohorte en
el store, borrarlas —hay auditoría, no hay política de retención—, o correr siempre con
ventana corta y dejarlas envejecer.

### Q8 — El plugin sueña sobre su propio desarrollo: ¿eso es un problema?

Las candidatas que salgan del store de desarrollo son memoria **sobre nightshift**, y se
inyectan en las sesiones que desarrollan nightshift. Es el dogfooding que el proyecto
quiere, y también es la única fuente de material real que hay hoy. La pregunta es si eso
contamina algo que después se publique: las trayectorias del benchmark corren en stores
desechables, así que a M4 no lo toca — pero conviene decidirlo a propósito y no por
omisión.
