# nightshift

**Una capa de memoria procedimental sobre la memoria declarativa nativa del agente.**
Una prueba de concepto, no un producto.

*[Read me in English](README.md)*

![El sueño proyecta trayectorias hacia bugs; la misma persona se los encuentra horas después en la pantalla](doc/assets/night.png)

> **Estado: M3 construido — captura, retrieval y dream fase 1, como plugin de Claude Code.**
> Todo lo de abajo corre. El código ya no es lo que bloquea el benchmark: lo que falta es
> **evidencia**. El gate de M1 son cinco sesiones reales, el de M3 tres noches sin
> intervención, y ninguno se juntó. Si algo de esto *ayuda* está sin medir: `verify` no
> existe, así que nada llega a `procedure` y ninguna memoria inyectada está verificada.

## Qué hace

Mira mientras trabajás. Cada comando, cada error y cada corrección se guarda como una
**trayectoria** — redactada, en tu máquina, en SQLite. De noche un sueño las consolida en
un **patrón**: qué forma tenía el problema, qué señal lo delató, un dibujo del mecanismo, y
una conjetura sobre con qué otras caras va a volver.

En la sesión siguiente, cuando describís lo que te está pasando, te lo devuelve. No *"el
timeout es 2000"* —eso lo sabe una memoria declarativa— sino *"esto ya se probó, alguien
subió el límite, se corrigió porque tapaba el síntoma, y ese camino descartado igual tenía
razón cuando el límite era genuinamente bajo"*.

En una frase: **que la próxima sesión no recorra de cero el camino que la anterior ya
recorrió.**

```mermaid
flowchart LR
  S["tu sesión"] -->|"7 hooks"| C["captura<br/>comando · error · corrección"]
  C --> R["redactor"] --> D[("SQLite<br/>local")]
  D -->|"de noche"| DR["dream<br/>dibuja · abstrae · proyecta"]
  DR --> D
  D -->|"tu primer prompt"| I["inyectado<br/>'esto ya se probó así'"]
  DR -. "M5 · no existe" .-> V["verify"] -. "nada llega acá" .-> P["procedure"]
  style V stroke-dasharray: 5 5
  style P stroke-dasharray: 5 5
```

## Qué no es

Claude Code ya trae **Auto Memory** (notas declarativas por repo) y **Auto Dream**
(consolidación en background). nightshift **no** los reemplaza y no compite en "notas +
sueño": corre encima ([ADR-001](doc/adr/ADR-001-no-competir-con-auto-dream.md)).

> Auto Memory recuerda *qué es verdad en este repo*. nightshift recuerda *cómo se
> averiguó*.

| | Capacidad | ¿Construida? |
|---|---|---|
| A | Memoria procedimental: la trayectoria, no sólo la conclusión | sí |
| B | Alternativas descartadas con **la precondición** que las hacía correctas | sí ([ADR-005](doc/adr/ADR-005-contraste-entre-implementaciones.md)) |
| C | Transferencia entre repositorios | apagada por defecto |
| D | Cada inyección trazable hasta su origen (`why`) | sí |
| E | Verificación: nada es procedimiento hasta que reproducirlo pase un gate | **no — es M5** |

E es la que importa, y es la que no existe.

## Correlo

```sh
git clone https://github.com/EvolvingAgentsLabs/nightshift
cd nightshift
./bin/nightshift init          # crea el store y resuelve deny_paths
claude --plugin-dir .          # cargalo en esta sesión
```

| Skill | Qué responde |
|---|---|
| `/nightshift:status` | qué hay guardado, qué se inyectó acá |
| `/nightshift:why <id>` | de dónde salió una inyección, paso por paso |
| `/nightshift:dream` | consolidar ahora en vez de esperar a la noche |
| `/nightshift:schedule` | instalar la corrida nocturna |
| `/nightshift:doctor` | ¿la captura está funcionando de verdad? |
| `/nightshift:dev` | arrancar una sesión de desarrollo sobre el plugin |

## La noche en que soñó sobre sí mismo

El 2026-08-27 a las 15:25 UTC el plugin consolidó el store de su propio desarrollo y, desde
el dibujo del mecanismo, **proyectó cuatro síntomas que nadie había observado**
([ADR-004](doc/adr/ADR-004-ideacion-y-proyeccion.md)). Esa misma tarde, midiendo por otro
motivo, dos resultaron ciertos:

| Lo que dream proyectó | Lo que se midió horas después |
|---|---|
| «El retrieval devuelve coincidencias por forma estructural sin relación con el contenido del trabajo.» | Dos prompts con síntomas distintos devolvían el mismo orden y los mismos scores |
| «Una revisión manual de un registro reciente muestra la estructura completa y todos los campos de texto en blanco.» | El prompt del propio dream mostraba seis pasos `(sin resumen)` de una trayectoria de 400 pasos que tenía 177 con contenido |

Tres cosas hay que decir, o es un cuento:

- **Ninguna se encontró *por* la proyección.** Estaban escritas, inyectadas y disponibles,
  y el trabajo las redescubrió midiendo. Una conjetura que nadie resuelve no es memoria:
  es una nota. Ese agujero es el que tantea
  [`experimentos/preguntar.py`](experimentos/preguntar.py).
- **El puntaje es cuatro proyecciones: dos confirmadas, una refutada, una abierta** — una
  candidata, un store. Una anécdota con numerador, y el numerador se puede contar:
  ```sh
  sqlite3 ~/.nightshift/trajectories.sqlite3 \
    "select projected_signals_json from trajectories where status='candidate';"
  ```
  Esta sección decía *«seis proyecciones: dos confirmadas, dos refutadas, dos abiertas»*.
  Dos de esas cuentas no existían. La corrección está en [`LATER.md`](LATER.md).
- **El mismo trabajo encontró tres defectos en el brazo del tratamiento.** Los tres eran
  invisibles porque todos los hooks salen 0 por diseño. Están arreglados; lo que importa es
  por qué pasaron semanas sin que nada los dijera.

## El defecto que apareció cuando alguien midió la promesa

El README de arriba promete que cuando *describís lo que te está pasando*, la memoria
vuelve. Nadie lo había medido. Medido sobre el store real: **enganchaba 1 paráfrasis de
6.** El mecanismo que este proyecto más publicita —que la memoria se enganche con un
problema antes de que su síntoma se haya visto una vez— sólo disparaba si usabas las
palabras del propio modelo.

La causa era un piso único para dos clases de texto que no se parecen: una oración que el
modelo destiló no tiene relleno, así que una palabra de contenido ya es señal; un volcado
de error es casi todo andamiaje del harness. Partido en dos, más una regla de que ninguna
coincidencia puede apoyarse sólo en palabras que dicen *que* algo se rompió y no *qué*:
**4 de 6**, con el control negativo en cero las dos veces.

Dos siguen fallando y no se arreglan por acá: `resumen`/`memoria consolidada`,
`métrica`/`contador de cobertura` no comparten una sola palabra. Eso es sinónimo, no
morfología; `difflib` y el emparejado por prefijo se midieron y no compran nada. Necesita
embeddings, que chocan con [ADR-003](doc/adr/ADR-003-modelo-de-dream.md). Espera.

Reproducilo: `python3 experimentos/05-enganche-por-parafrasis.py --alternativas`

## La parte honesta

El benchmark que respondería *"¿recordar cómo se averiguó algo mejora a un agente que ya
tiene memoria declarativa?"* tiene su runner, sus tres repos fixture y su adaptador de
agente — y **nunca corrió**, porque el pre-registro sigue en borrador. Todo lo que se
inyecta hoy es una `candidate`: la abstrajo un modelo, no la reprodujo nadie.

Un ensayo no es evidencia, una demostración no es un resultado, y una proyección que se
cumplió dos veces tampoco.

- [`doc/00-spec.md`](doc/00-spec.md) — la spec
- [`doc/PLAN-v0.3.md`](doc/PLAN-v0.3.md) · [`doc/PLAN-M4.md`](doc/PLAN-M4.md) — el plan y el benchmark
- [`doc/adr/`](doc/adr/) — las decisiones y lo que costó cada una
- [`experimentos/`](experimentos/) — experimentos que se corren solos, incluidos los que no favorecen al plugin
- [`LATER.md`](LATER.md) — todo lo encontrado y no arreglado

## Licencia

Apache 2.0. Ver [`LICENSE`](LICENSE).
