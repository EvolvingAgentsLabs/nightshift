# ADR-001 — Por qué no competir con Auto Dream

| Campo | Valor |
|---|---|
| Estado | **Propuesto** — pendiente de revisión de Ismael (gate de M0) |
| Fecha | 2026-08-26 |
| Contexto | spec v0.3 §1.1, §1.3.4, §8.3 |
| Decisión reversible | No sin rehacer la tesis del proyecto |

## Contexto

nightshift v0.2 se diseñó cuando Claude Code no tenía memoria propia. La propuesta de
valor era, en la práctica, "dale memoria a tu agente".

Claude Code ahora trae dos cosas de fábrica:

- **Auto Memory** — notas declarativas por repositorio, en
  `~/.claude/projects/*/memory/`, cargadas automáticamente.
- **Auto Dream** — consolidación en background de esas notas.

Eso vacía la propuesta original. Un proyecto externo que capture notas y las consolide
de noche está construyendo, con menos integración y menos acceso, algo que el harness
ya hace gratis y mejor. Hay tres razones estructurales por las que perderíamos:

1. **Acceso al contexto.** El nativo ve el transcript completo. Nosotros vemos los
   payloads que los hooks nos pasan, que son un subconjunto y cambian entre versiones.
2. **Coste de distribución.** El nativo está encendido por defecto. Nosotros pedimos
   una instalación.
3. **Ritmo.** Anthropic itera el harness más rápido de lo que nosotros iteramos un
   proyecto de fin de semana. Cada mejora suya nos borra una feature.

Competir en "notas + sueño" es elegir una pelea que se pierde por construcción, no por
ejecución.

## Decisión

**nightshift no compite con Auto Memory ni con Auto Dream. Corre encima de ellos.**

Concretamente:

1. El posicionamiento es *procedural memory layer over the agent's native declarative
   memory*. Prohibido el encuadre de reemplazo en README, ADRs, commits y demos.
2. nightshift **nunca escribe** bajo `~/.claude/projects/*/memory/`. Lee `MEMORY.md`
   sólo como señal de retrieval. Desinstalar nightshift deja la memoria nativa
   bit-idéntica. (spec §1.3.4)
3. El baseline del benchmark es **Auto Memory + Auto Dream encendidos**, no un agente
   sin memoria. (spec §10.1)
4. nightshift sólo invierte donde lo nativo no puede llegar **por diseño**, no por
   inmadurez: las capacidades A, B, C, D y E de spec §1.2.

## Por qué esas cinco capacidades y no otras

El filtro que se aplicó fue: *¿esto le falta al nativo por diseño, o por no haberlo
hecho todavía?* Sólo lo primero sobrevive, porque lo segundo aparece en la próxima
release y nos borra.

| # | Capacidad | Por qué el nativo no puede, por diseño |
|---|---|---|
| A | Trayectorias causales | Auto Memory es declarativa: almacena proposiciones sobre el repo. La cadena hipótesis → tools → señal decisiva → fix no es una proposición; es un proceso, y ese proceso se descarta al escribir la nota. |
| B | Alternativas descartadas con precondiciones | Auto Dream consolida **borrando** lo contradicho: es lo correcto para una base de hechos, donde una contradicción es un error. En memoria procedimental, "esto no funcionó **cuando** X" es la información más valiosa. Los objetivos son incompatibles, no es una carencia. |
| C | Cross-repo / cross-harness | Auto Memory está sellada por repo, y eso es una decisión de privacidad correcta. La única forma de cruzar es abstraer y redactar antes de persistir — asumir el coste del redactor determinista y de `deny_paths`. El nativo no puede asumirlo sin romper su propia garantía. |
| D | Consolidación verificable | El nativo consolida por juicio del modelo. Verificar requiere un gate del usuario, un worktree y una re-ejecución: infraestructura que el harness no puede imponerle a todos sus usuarios. Nosotros sí, porque nos instala quien lo quiere. |
| E | Captura pre-`/compact` | El razonamiento intermedio muere en la compactación. El nativo compacta hacia notas declarativas; el paso intermedio no se conserva porque no es lo que la memoria declarativa quiere guardar. |

Las cinco pasan el filtro. Cualquier feature futura que no lo pase va a `LATER.md`,
no al roadmap.

## Consecuencias

**Aceptadas:**

- El benchmark es **más difícil de ganar**. S0 ya tiene memoria. Es el punto: una
  ganancia contra este baseline es real, y una derrota es información honesta.
- Renunciamos a la demo fácil ("mirá, ahora recuerda"). El nativo ya la hace.
- Dependemos de la estabilidad de los hooks del harness. Mitigación: los nombres y el
  formato se re-verifican al inicio de cada milestone que toque hooks, con fecha en la
  spec (§5.4).
- El valor sólo se ve en tareas donde el *proceso* importa: debugging recurrente,
  transferencia entre repos. En tareas de una sola pasada, nightshift no aporta nada
  y no debe fingir que sí.

**Ganadas:**

- Cada mejora de Auto Memory nos **beneficia** en vez de borrarnos: mejora S0 y mejora
  S1, y nosotros medimos el delta.
- La tesis se vuelve falsable. M4 puede matar el proyecto, y eso está escrito antes de
  correrlo (`bench/PREREG.md`).

## Alternativas consideradas

1. **Reemplazar Auto Memory.** Rechazada: perdemos en acceso, distribución y ritmo
   (los tres puntos del Contexto). Además obliga a escribir en su directorio, lo que
   rompe la garantía de desinstalación limpia.
2. **Hacer un fork / parche del harness.** Rechazada: no es sostenible, y convierte
   cada release de Claude Code en un incidente.
3. **Ignorar el nativo y medir contra "sin memoria".** Rechazada explícitamente. Daría
   números buenos y falsos. Es la alternativa que más nos costó descartar y la razón
   principal por la que existe este ADR.
4. **Congelar el proyecto ya.** Considerada seriamente. Rechazada *condicionalmente*:
   se congela si M4 no muestra ganancia. La diferencia entre esta alternativa y la
   decisión tomada es solamente que aceptamos pagar M1–M4 para averiguarlo con datos.

## Qué revisar (para Ismael — este es el gate de M0)

1. ¿La tabla de "por qué el nativo no puede, por diseño" se sostiene para **las cinco**?
   Si alguna es "todavía no lo hicieron" en vez de "por diseño", hay que sacarla del
   roadmap ahora, no en M4.
2. ¿El baseline S0 es honesto, o hay una configuración de Auto Memory + Auto Dream que
   lo haría más fuerte y que estamos omitiendo?
3. ¿La condición de coexistencia (§1.3.4) es suficiente, o hay formas de interferir con
   la memoria nativa que no pasan por escribir en su directorio?
4. ¿Falta alguna capacidad que pase el filtro y que no esté en la lista?
