# nightshift

**Una capa de memoria procedimental sobre la memoria declarativa nativa del agente.**
Una prueba de concepto, no un producto.

*[Read this in English](README.md)*

> **Estado: M3 construido — captura, retrieval y dream fase 1, como plugin de Claude Code.**
> Todo lo que se describe abajo funciona, y el código ya no es lo que bloquea el
> benchmark: lo que falta es **evidencia**. El gate de M1 son cinco sesiones reales y el
> de M3 tres noches sin intervención, y ninguna de las dos está juntada. Si *sirve* sigue
> sin medirse: `verify` no existe, así que nada llega a `procedure` y nada de lo inyectado
> está verificado.

## Qué hace

nightshift mira por encima del hombro mientras trabajás: cada comando, cada error y cada
corrección quedan guardados como una **trayectoria** — redactada, en tu máquina, en un
SQLite. A la noche un dream la consolida en un **patrón**: qué forma tenía el problema,
qué señal lo delató, más un diagrama del mecanismo y una conjetura de en qué otras caras
va a volver a aparecer. Cuando abrís la sesión siguiente y escribís lo que te está
pasando, te devuelve eso: no *«el timeout está en 2000»*, que es lo que sabe una memoria
declarativa, sino *«esto ya se intentó así, se probó subir el límite, alguien lo corrigió
porque tapaba el síntoma, y el camino descartado seguía siendo el correcto cuando el
límite era genuinamente bajo»*. En una frase: **para que la próxima sesión no empiece de
cero el mismo camino que la anterior ya recorrió.**

```mermaid
flowchart LR
  S["tu sesión"] -->|"7 hooks"| C["captura<br/>comando · error · corrección"]
  C --> R["redactor determinista"]
  R --> D[("store local<br/>SQLite")]
  D -->|"de noche"| DR["dream · consolidate<br/>dibuja el mecanismo<br/>abstrae el patrón<br/>proyecta otras caras<br/>contrasta lo descartado"]
  DR --> D
  D -->|"al abrir · al escribir"| I["inyectado como contexto<br/>'esto ya se intentó así'"]
  I --> N["sesión siguiente"]
  DR -. "M5 · no existe" .-> V["verify<br/>reproducir contra un gate"]
  V -. "nada llega acá" .-> P["procedure<br/>verificado"]

  style V stroke-dasharray: 5 5
  style P stroke-dasharray: 5 5
```

## Qué no es

Claude Code ya trae **Auto Memory** (notas declarativas por repo) y **Auto Dream**
(consolidación en background). nightshift **no** los reemplaza y no compite en «notas +
sueño»: corre encima ([ADR-001](doc/adr/ADR-001-no-competir-con-auto-dream.md)).

> Auto Memory recuerda *qué es verdad en este repo*. nightshift recuerda *cómo se
> averiguó*.

## Las cinco capacidades que reclama

| | Capacidad | ¿Construida? |
|---|---|---|
| A | Memoria procedimental: la trayectoria, no sólo la conclusión | sí |
| B | Alternativas descartadas **con la precondición** que las hacía correctas | sí ([ADR-005](doc/adr/ADR-005-contraste-entre-implementaciones.md)) |
| C | Transferencia entre repositorios | apagada por defecto |
| D | Toda inyección rastreable a su origen (`why`) | sí |
| E | Verificación: nada es procedimiento hasta que reproducirlo pasa un gate | **no — eso es M5** |

E es la que importa, y es la que no existe.

## Instalarlo y correrlo

```sh
git clone https://github.com/EvolvingAgentsLabs/nightshift
cd nightshift
./bin/nightshift init          # crea el store y resuelve deny_paths
claude --plugin-dir .          # cargarlo en esta sesión
```

Y adentro de esa sesión:

| Skill | Qué contesta |
|---|---|
| `/nightshift:status` | qué hay guardado, qué se inyectó acá |
| `/nightshift:why <id>` | de dónde salió una inyección, paso por paso |
| `/nightshift:dream` | consolidar ahora en vez de esperar la noche |
| `/nightshift:schedule` | instalar la corrida nocturna |
| `/nightshift:doctor` | si la captura está funcionando de verdad |
| `/nightshift:dev` | arrancar una sesión de desarrollo sobre el propio plugin |

## La noche en que soñó sobre sí mismo

El 2026-08-27 el plugin consolidó el store de su propio desarrollo y, desde el dibujo del
mecanismo, **proyectó cuatro síntomas que nadie había observado**
([ADR-004](doc/adr/ADR-004-ideacion-y-proyeccion.md)). Esa misma tarde, midiendo por otro
motivo, dos resultaron ciertos:

| Lo que dream proyectó a las 15:25 | Lo que se midió horas después |
|---|---|
| «El retrieval devuelve coincidencias por forma estructural sin relación con el contenido del trabajo.» | Dos prompts con síntomas distintos devolvían el mismo orden y los mismos scores: el retrieval de lo crudo no miraba el prompt |
| «Una revisión manual de un registro reciente muestra la estructura completa y todos los campos de texto en blanco.» | El prompt del propio dream mostraba seis pasos `(sin resumen)` de una trayectoria de 400 pasos que tenía 177 con contenido |

Tres cosas hay que decir de eso, o es un cuento:

- **Ninguna se encontró *por* la proyección.** Estaban escritas, inyectadas y
  disponibles, y el trabajo las redescubrió midiendo. Una conjetura que nadie resuelve no
  es memoria: es una nota. Ese agujero es el que tantea
  [`experimentos/preguntar.py`](experimentos/preguntar.py), que muestra cada proyección
  con opciones para que una persona la resuelva, sin escribir en el store y **sin
  promover nada** — que un humano diga que sí no es una reproducción contra un gate
  ([ADR-002](doc/adr/ADR-002-verify-gate.md)).
- **De las otras dos, una se comprobó contra el código y no se sostenía; la otra sigue
  abierta.** Cuatro proyecciones: dos confirmadas, una refutada, una abierta — una
  candidata, un store. Es una anécdota con numerador, no un resultado, y el numerador se
  puede contar:
  ```sh
  sqlite3 ~/.nightshift/trajectories.sqlite3 \
    "select projected_signals_json from trajectories where status='candidate';"
  ```
  Acá decía *«seis proyecciones: dos confirmadas, dos refutadas, dos abiertas»*. Dos de
  esas cuentas no existían. La corrección está en [`LATER.md`](LATER.md); que el número
  inflado sobreviviera en el único lugar donde este proyecto publica su puntaje es el
  mismo modo de falla que el repo lleva tres secciones documentando.
- **La misma sesión encontró tres defectos en el brazo del tratamiento** — el retrieval
  que no miraba el prompt, dream leyendo pasos vacíos, y el ensayo culpando a dream de su
  propio `HOME` roto. Los tres eran invisibles porque todos los hooks salen 0 por diseño.
  Están arreglados; lo que importa es por qué pasaron semanas sin que nada los dijera.

## La parte honesta

El benchmark que contestaría *«¿recordar cómo se averiguó algo mejora el trabajo de un
agente que ya tiene memoria declarativa?»* tiene su runner, sus tres repos fixture y su
adaptador de agente — y **no corrió nunca**, porque el pre-registro sigue siendo un
borrador con decisiones abiertas. Todo lo que se inyecta hoy es una `candidate`:
abstraída por un modelo, reproducida por nadie.

Un ensayo no es evidencia, y una demostración no es un resultado. Una proyección que
acertó dos veces, tampoco.

- [`doc/00-spec.md`](doc/00-spec.md) — la spec
- [`doc/PLAN-v0.3.md`](doc/PLAN-v0.3.md) · [`doc/PLAN-M4.md`](doc/PLAN-M4.md) — el plan y el benchmark
- [`doc/adr/`](doc/adr/) — las decisiones y qué costó cada una
- [`experimentos/`](experimentos/) — experimentos que se corren solos, incluidos los que no favorecen al plugin
- [`experimentos/preguntar.py`](experimentos/preguntar.py) — human-in-the-loop sobre lo que dream sólo conjeturó: sólo lectura del store, no promueve nada
- [`LATER.md`](LATER.md) — todo lo encontrado y no arreglado

## Licencia

Apache 2.0. Ver [`LICENSE`](LICENSE).
