# HANDOFF — control del desarrollo

Documento para la sesión de Claude Code que continúa el desarrollo de nightshift.
Se lee entero antes de tocar nada.

---

## 0. Qué sos en esta sesión

Estás corriendo **dentro del plugin que vas a modificar**. Si la sesión se abrió con
`claude --plugin-dir .`, los hooks que están capturando esta conversación son el código
de este working tree. Editar `nightshift/hook.py` cambia cómo se captura tu próxima
tool call.

Eso tiene dos consecuencias prácticas:

- Podés probar tus cambios contra vos mismo. `nightshift status` a mitad de sesión te
  muestra la trayectoria que estás generando ahora.
- Un bug que rompa la captura no te va a dar un error: los hooks salen 0 siempre
  (spec §7.2). El silencio no es evidencia de que funciona. Por eso existe
  `nightshift selftest`, y por eso hay que correrlo.

Arrancá con `nightshift dev`.

---

## 1. Estado real

### Construido y en `main`

| Pieza | Dónde |
|---|---|
| Captura por 7 hooks | `nightshift/hook.py`, `hooks/hooks.json` |
| Redactor determinista | `nightshift/redact.py` |
| Store SQLite + export `trajectory.v1` | `nightshift/store.py` |
| Retrieval estructural e inyección | `nightshift/retrieve.py` |
| Auditoría del store (gate de M1) | `nightshift/audit.py` |
| Dream fase 1 — `consolidate` | `nightshift/dream.py` |
| Scheduler pluggable + registro de corridas | `nightshift/schedule.py` |
| CLI y skills | `nightshift/cli.py`, `skills/` |
| Gate | `make check` — lint-docs, lint-code, schema, 106 tests, selftest |
| Gate con modelo local | `make dream-selftest` — fuera de `check` a propósito |

### No construido

Dream fase 2 (`verify`) y el benchmark. Hay `candidate`, pero **nada llega a
`procedure`**: ninguna memoria inyectada está verificada. Una `candidate` la abstrajo un
modelo local y nadie la reprodujo contra un gate. No lo describas como si lo estuviera,
ni en el README, ni en un commit, ni en una demo.

### Bloqueado por una persona, no por vos

- **M4 (benchmark go/no-go)** — lee umbrales de `bench/PREREG.md`, donde hay 19
  `TODO(Matias)`. **Completar uno es una violación, no una ayuda.** Podés construir el
  runner del benchmark; no podés inventar los números que decide.
- **M5 (verify)** — prohibido empezarlo antes del veredicto de M4. No es una
  preferencia de estilo: verify es lo más caro de construir y sólo vale la pena si la
  memoria procedimental cruda ya mostró ganancia (plan §3).
- **Gate humano de M0** — la revisión de ADR-001 por Ismael sigue pendiente, y M1/M2 ya
  se construyeron sobre las cinco capacidades que ese ADR decide. Si la revisión tumba
  una fila, hay código que sobra. No lo des por cerrado.

---

## 2. Reglas que no se negocian

Están en `CLAUDE.md` y las repito porque son las que se rompen sin querer:

1. **Un milestone por rama.** PR sólo si el gate pasa, y el gate es un script.
2. **Cada sesión termina en commit medible.** Si no hay commit, el motivo va a
   `LATER.md`. No hay tercera opción.
3. **Sólo librería estándar.** Ningún import de tercero, en `nightshift/` ni en
   `tests/`. `make lint-code` lo verifica.
4. **Sin red.** Ningún `socket`, `urllib`, `http`, `requests` en `nightshift/`.
   El modelo local se invoca por `subprocess`, no por HTTP.
5. **Nunca escribir bajo `~/.claude/projects/*/memory/`.** Sólo `config.py`,
   `context.py` y `cli.py` pueden siquiera nombrar esa ruta.
6. **Los hooks nunca bloquean ni ensucian stdout.** Salida: JSON válido o nada.
7. **No agregues features que no estén en el plan.** Si parece buena idea, va a
   `LATER.md`.

---

## 3. Hechos ya verificados — no los re-derives

Verificados contra `https://code.claude.com/docs/en/hooks` el 2026-08-26, y algunos
descubiertos corriendo el plugin. Están en la spec; acá van resumidos para que no
pierdas tiempo redescubriéndolos:

- `PostToolUse` **no dispara en fallos**. Los fallos van a `PostToolUseFailure`.
- `PreCompact` **no trae el transcript**: sólo `session_id`, `cwd`, `compaction_reason`.
  Es señal de sellado, no fuente de datos.
- `Stop` dispara al final de **cada turno**, no de la sesión. Cierra `SessionEnd`.
- `additionalContext` va al contexto del modelo; `systemMessage` a la pantalla del
  usuario. No son intercambiables.
- Las skills de plugin llevan namespace: `/nightshift:status`, no `/nightshift status`.
- Los cambios en `nightshift/*.py` **no** necesitan `/reload-plugins` — cada hook
  arranca un proceso nuevo. El reload es para `hooks/hooks.json`, skills y manifiesto.
- `CLAUDE_PLUGIN_DATA` llega a los hooks pero **no** al Bash tool. Por eso el store se
  fija en `~/.nightshift` y esa variable se ignora a propósito.

Si alguno deja de ser cierto porque cambió el harness, actualizá `doc/00-spec.md` §5 en
el mismo commit y dejá la fecha.

---

## 4. Cola de trabajo

**T1 a T5 están hechas y en `main`.** Lo que sigue es qué las cerró y qué quedó abierto.

| Tarea | Estado | Qué la cerró |
|---|---|---|
| T1 — `nightshift audit` | ✅ #4 | `audit` recorre todo lo persistido y afirma que no hay fugas. Sobre el store real: **cero hallazgos**. `--min-sessions 5` sigue saliendo 1 por conteo de sesiones (ver abajo). |
| T2 — retrieval por tipo de tarea | ✅ #5 | `general` dejó de puntuar como coincidencia de tipo, y el retrieval se rehace en el primer `UserPromptSubmit` clasificado, sin re-inyectar lo ya dicho. Spec §5.7. |
| T3 — trayectorias huérfanas | ✅ #6 | `SessionStart` cierra las `open` de otras sesiones sin actividad hace más de `orphan_after_hours`. Corte por inactividad, nunca por antigüedad. Spec §5.8. |
| T4 — M3-a dream `consolidate` | ✅ #7 | Agrupación determinista, modelo local sólo para abstraer, salida validada contra esquema + redactor + auditor. Gate: `make dream-selftest`. |
| T5 — M3-b scheduler | ✅ | `launchd` / `systemd` (timer de usuario) / `loop`, con registro de corridas. Gate: `nightshift schedule status` reporta las últimas y sus resultados. |

### Lo que falta, y de quién es

**Ninguna de estas tres es código pendiente. Son decisiones o evidencia.**

1. **El gate de M1: dos sesiones más.** `nightshift audit` no encuentra ninguna fuga en
   el store real, pero hay 3 sesiones distintas capturadas de las 5 que pide el gate.
   Se cierra usando el plugin, no escribiendo código.
   ```sh
   nightshift audit --min-sessions 5
   ```

2. **El gate de M3: tres noches.** El scheduler está y las corridas quedan registradas.
   Falta instalar el timer en la Air y dejarlo correr tres noches seguidas sin
   intervención. Lo hace una persona.
   ```sh
   nightshift schedule install     # toca el gestor de arranque: no lo corre un agente solo
   nightshift schedule status      # a la mañana siguiente
   ```

3. **El gate humano de M0.** La revisión de ADR-001 por Ismael sigue pendiente, y ahora
   hay más código construido sobre las cinco capacidades que ese ADR decide.

### Bloqueado — no empieces

- **M4.** Podés construir el runner del benchmark (las tres familias, las filas S0/S1, el
  reporte). **No** podés fijar umbrales ni criterios de éxito: eso es `bench/PREREG.md`,
  tiene 19 `TODO(Matias)`, y el pre-registro se congela **antes** de correr nada.
  Completar un `TODO(Matias)` es una violación, no una ayuda.
- **M5 (`verify`).** Prohibido hasta que M4 dé veredicto. Hoy nada llega a `procedure`, y
  eso es correcto: ninguna memoria inyectada está verificada.
- **Adapter de OpenCode.** Prohibido.

### Si vas a tocar dream

Dos cosas que cuestan tiempo si se redescubren:

- `ollama` re-acomoda las palabras al ancho de la terminal aunque stdout sea un pipe:
  vuelve el cursor con `ESC[nD` y reescribe. Borrar los escapes a secas deja fragmentos
  duplicados y saltos de línea **dentro de strings JSON**. Se usa `--nowordwrap`, y
  `dream.undo_wrapping()` es la red para versiones que no lo tengan.
- `--think false` baja una llamada de 56s a 6s con el mismo modelo.

La agrupación es por tipo de tarea y nada más. Agrupar por firma de herramientas dejaba
grupos de uno, y un grupo de uno no puede tener contradicciones. Agrupar mejor necesita
volumen real, no otra intuición: está en `LATER.md`.

## 5. Cómo se entrega cada tarea

```sh
git checkout -b <rama>
# ... trabajás ...
make check          # lint-docs + lint-code + schema + tests + selftest
nightshift selftest # otra vez, desde la sesión, contra el código nuevo
git commit
git push -u origin <rama>
```

PR sólo con el gate en verde. En el cuerpo del PR: qué cambió, **qué gate lo prueba**, y
qué quedó afuera.

**Antes de cada commit, dos preguntas honestas:**

1. ¿Agregué un test que falla si mi cambio se revierte? Si no, no agregué un test.
2. ¿Estoy describiendo lo que construí, o lo que quería construir? El README y los
   commits de este repo dicen explícitamente qué no funciona. Mantené eso.

Si el gate no pasa y no sabés por qué, **no lo relajes**. Los checks de `lint-code` no
son estilo: cada uno defiende una prohibición del proyecto. Un check que molesta es
casi siempre un check que está haciendo su trabajo.

---

## 6. Prompt de arranque

Para pegar en la sesión que toma el control:

```
Leé doc/HANDOFF.md entero, después CLAUDE.md y doc/00-spec.md.

T1 a T5 están en main. Lo que falta de M1 y M3 es evidencia, no código: dos
sesiones reales más para `nightshift audit --min-sessions 5`, y tres noches con
el timer instalado para `nightshift schedule status`. Las dos las corre una
persona.

Si vas a construir algo, es el runner del benchmark de M4 — las tres familias,
las filas S0/S1, el reporte — y **sin fijar un solo umbral**: los 19
TODO(Matias) de bench/PREREG.md los resuelve Matías, y completar uno es una
violación. No empieces M5 antes del veredicto de M4. Rama propia, gate en
verde, PR, y un resumen de qué quedó en LATER.md.
```
