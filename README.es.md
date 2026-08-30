# nightshift

**Un motor de memoria procedimental y epistemológica.**
Una prueba de concepto, no un producto.

*[Read me in English](README.md)*

![El sueño proyecta trayectorias hacia bugs; la misma persona se los encuentra horas después en la pantalla](doc/assets/night.png)

> **Estado: M3 construido** — captura, retrieval y dream fase 1, como plugin de Claude
> Code. El gate es `make dogfood`.
>
> **Todo lo de esta página es una hipótesis sobre dónde encaja esta arquitectura, no un
> registro de lo que hizo.** nightshift sólo corrió sobre su propio repositorio. Nadie
> midió que ayude ni siquiera ahí: `verify` no existe, nada llega a `procedure` y toda
> memoria que inyecta está sin verificar. Leé los dominios de abajo como *"ésta es la
> forma de problema para la que se construyó la máquina"*, nunca como casos de éxito.

---

El núcleo de nightshift no es sobre código. Su capacidad real es capturar la **Cadena de
Ejecución** (CTE), destilarla en un **mecanismo abstracto — una escena física** — y
**proyectar síntomas futuros** antes de que ocurran, preservando las alternativas
descartadas con las precondiciones que las hacían correctas.

Si sacamos a nightshift del IDE y de Claude Code, éstos son los dominios para los que su
arquitectura tiene forma.

## 1 · Ciberseguridad: threat hunting y respuesta a incidentes

Los analistas del SOC persiguen anomalías. Un atacante usa el mismo mecanismo subyacente
pero cambia la *cara* del ataque: el síntoma.

- **La trayectoria:** la secuencia del analista — `alerta → query a logs → hipótesis falsa
  → query a red → descubrimiento de exfiltración`.
- **El sueño:** dibuja el mecanismo táctico del atacante (*"el atacante usa una tubería
  legítima, pero en horario muerto"*).
- **La proyección:** qué otras alertas generaría ese mecanismo — *"picos de CPU en los
  servidores de backup"*.
- **El gancho:** cuando un analista junior ve un síntoma proyectado meses después, vuelve
  el procedimiento: *"alguien ya investigó este patrón; no mires el malware, mirá los
  crons programados — y bloquear la IP se descartó porque era spoofed."*

## 2 · Diagnóstico diferencial en medicina interna

El diagnóstico clínico es, por definición, una cadena de ejecución: síntoma → examen
físico → estudio de laboratorio (negativo) → corrección de hipótesis → diagnóstico.

- **Ideación física, literal.** Un proceso patológico *es* un mecanismo físico — *"una
  válvula tapada que acumula presión hacia atrás"*. Es el único dominio donde el medio por
  defecto no es una metáfora del mecanismo: es el mecanismo.
- **El problema que ataca:** los pacientes presentan a menudo síntomas atípicos de una
  enfermedad común, y ésos son exactamente los que un mecanismo puede proyectar. Ante
  *"dolor en hombro + hipo"*, volvería la trayectoria que una vez lo rastreó hasta una
  irritación del diafragma por un problema hepático — antes de que se pida otra
  radiografía de hombro.

> Éste lleva una advertencia que los otros no. Un motor de memoria que sugiere qué
> estudios saltear es un sistema de apoyo a la decisión clínica, y ésos son regulados,
> validados y auditados. nightshift no es ninguna de las tres cosas y no llega a
> `procedure`: sería insumo para un clínico, nunca una recomendación, y necesitaría la
> etapa de verificación que sigue sin construirse antes de acercarse a un paciente.

## 3 · Helpdesk: cerrar la brecha de Nivel 3 a Nivel 1

Los ingenieros de Nivel 3 resuelven problemas de infraestructura que en Nivel 1 se
manifiestan de formas estúpidas — *"el botón de imprimir sale gris"* porque el
microservicio de facturación saturó el pool de conexiones.

- **La proyección:** Nivel 3 resuelve el bug; se sueña el mecanismo y se proyecta qué
  otros tickets van a empezar a llegar — *"la app móvil dará timeout"*, *"los reportes
  saldrán en blanco"*.
- **El valor:** cuando el usuario final llama a Nivel 1 quejándose de la app móvil, la
  paráfrasis engancha la memoria procedimental y el agente de Nivel 1 recibe el paliativo
  en vez de escalar el ticket.

## 4 · Mantenimiento industrial y robótica

El ejemplo que salió del store de este repo — *"tamiz sin agujero: por una cinta viajan
bidones cerrados…"* — es literalmente mantenimiento industrial.

- **La trayectoria:** lecturas de sensores más acciones del operario — `apaga motor →
  purga válvula → el error persiste → cambia filtro → se soluciona`.
- **El sueño:** abstrae la falla mecánica y proyecta qué otros sensores van a dar lecturas
  anómalas si vuelve a pasar.
- **Precondiciones (capacidad B):** *"bajar la presión de la bomba resolvió la alerta,
  pero se descartó porque ralentizaba la producción. Ese camino era correcto cuando el
  líquido era de alta viscosidad."*

## 5 · Memoria corporativa y estrategia legal

Las empresas pierden fortunas repitiendo estrategias descartadas porque nadie recuerda
*por qué* se descartaron, ni *bajo qué condiciones* eran correctas.

- **La capacidad B ([ADR-005](doc/adr/ADR-005-contraste-entre-implementaciones.md)) es la
  clave acá.** Trayectorias de decisiones: M&A, apuestas de marketing, litigios.
- **La memoria:** *"intentamos comprar la empresa X. Hicimos el análisis Y. Descubrimos el
  pasivo Z. Descartamos la compra."*
- **El gancho:** años después la dirección propone comprar la empresa W, estructuralmente
  parecida. Lo que vuelve: *"esta estructura ya se investigó. Auditar sus patentes es una
  trampa de tiempo; vayan directo a los pasivos laborales. Licenciar su tecnología era
  válido sólo con la tasa por debajo del 3%."*

## 6 · Diseño de videojuegos y QA testing

Los speedrunners y los testers de QA rompen juegos encadenando acciones que no deberían
interactuar.

- **La trayectoria:** la secuencia de inputs — `saltar → abrir inventario → recibir daño →
  estado de invulnerabilidad`.
- **Ideación y proyección:** dibuja el mecanismo del motor (*"la interrupción de animación
  desincroniza el flag de colisión"*) y proyecta qué otras combinaciones de ítems y
  acciones explotan el mismo.
- **Inyección:** señala parchear **el mecanismo abstracto** en vez de ese glitch puntual,
  anticipándose a exploits que los jugadores todavía no descubrieron.

## Qué tienen en común los seis

nightshift no es "un asistente para programadores". Es un **motor de anticipación de
fallos basado en experiencia empírica**. Cualquier dominio donde el costo de repetir una
investigación desde cero sea alto, y donde un mismo fallo sistémico tenga múltiples
síntomas, es la forma para la que se construyó.

Si de verdad entrega eso es la pregunta abierta, y está abierta en sentido estricto: el
benchmark que la respondería tiene runner, tres repos de fixture y un adapter de agente, y
**nunca corrió**.

## Qué de eso está construido

Cada dominio de arriba se apoya en alguna de estas cinco capacidades. Éste es su estado
real, y la última fila es la razón por la que ninguno de los seis es un caso de éxito:

| | Capacidad | ¿Construida? |
|---|---|---|
| A | Memoria procedimental: la trayectoria, no sólo la conclusión | sí |
| B | Alternativas descartadas guardadas **con la precondición** que las hacía correctas | sí ([ADR-005](doc/adr/ADR-005-contraste-entre-implementaciones.md)) |
| C | Transferencia entre repositorios — o entre casos, pacientes, tickets, máquinas | apagada por defecto |
| D | Cada inyección trazable hasta su origen (`why`) | sí |
| E | Verificación: nada es procedimiento hasta que reproducirlo pasa un gate | **no — eso es M5** |

**E es la que importa, y es la que no existe.** Hasta que exista, toda memoria es
`candidate`: la abstrajo un modelo, no la reprodujo nadie. En un repositorio de código eso
significa tratarla como pista. En un hospital, un SOC o una sala de due diligence
significa algo más fuerte: no es usable como recomendación.

## Correlo

```sh
git clone https://github.com/EvolvingAgentsLabs/nightshift
cd nightshift
./bin/nightshift init          # crea el store, resuelve deny_paths
claude --plugin-dir .          # cargalo en esta sesión

make dogfood                   # el gate: check + doctor + audit + status, sobre el store REAL
make experiments               # cuáles hipótesis del proyecto están comprobadas
```

| Skill | Qué contesta |
|---|---|
| `/nightshift:status` | qué hay guardado, qué se inyectó acá |
| `/nightshift:why <id>` | de dónde salió una inyección, paso por paso |
| `/nightshift:resolve` | ¿pasó un síntoma proyectado? registralo, con evidencia |
| `/nightshift:dream` | consolidar ahora en vez de esperar a la noche |
| `/nightshift:sleep` | sellar el capítulo en curso y soñar con él, a mitad de sesión |
| `/nightshift:schedule` | instalar la corrida nocturna |
| `/nightshift:doctor` | ¿la captura está funcionando de verdad? |
| `/nightshift:dev` | empezar una sesión de desarrollo sobre el plugin mismo |

## Dónde mirar después

- [`doc/COMO-FUNCIONA.md`](doc/COMO-FUNCIONA.md) — **cómo funciona la máquina**: los cuatro pasos, las tres ideas, qué está construido y qué no
- [`doc/00-spec.md`](doc/00-spec.md) — la spec
- [`doc/BITACORA.md`](doc/BITACORA.md) — qué pasó de verdad, en su tamaño real
- [`doc/adr/`](doc/adr/) — las decisiones y lo que costó cada una
- [`experimentos/`](experimentos/) — experimentos que se corren, incluidos los que no favorecen al plugin
- [`LATER.md`](LATER.md) — todo lo encontrado y no arreglado

## Licencia

Apache 2.0. Ver [`LICENSE`](LICENSE).
