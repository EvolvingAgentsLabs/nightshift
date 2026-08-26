# ADR-002 — Verify gate: qué cuenta como reproducción

| Campo | Valor |
|---|---|
| Estado | **Propuesto** — se implementa en M5, sólo si M4 pasa |
| Fecha | 2026-08-26 |
| Contexto | spec v0.3 §4.2, §6.2, §6.3 |
| Depende de | ADR-001 (capacidad D) |

## Contexto

La capacidad D de la tesis es *consolidación verificable*: una trayectoria se convierte
en procedimiento sólo si reproducirla pasa un gate. Es la diferencia con Auto Dream,
que consolida por juicio del modelo.

Eso deja una pregunta sin la cual "verificable" es marketing: **qué cuenta exactamente
como reproducción**. Si la respuesta la da un LLM, no ganamos nada — cambiamos un
juicio de modelo por otro con más pasos.

Este ADR fija la definición antes de que exista el código, para que M5 no pueda
relajarla bajo presión de resultados.

## Decisión

Una trayectoria `candidate` se promueve a `procedure` si y sólo si se cumplen **las
cinco** condiciones siguientes.

### 1. Existe un `gate_id` declarado por el usuario

Un gate es un **comando** provisto por el usuario, registrado en la config de
nightshift, que sale `0` o distinto de `0`. Ejemplos: `pytest tests/parser`,
`make check`, `npm test -- --run`.

- nightshift **no infiere ni genera gates**. Si el usuario no declaró uno para ese
  tipo de tarea, la trayectoria no es verificable y se queda en `candidate`.
- Un gate cuyo criterio de éxito lo evalúa un modelo **no es un gate**. Sin excepciones,
  ni siquiera "el modelo lee el output del test". El exit code es el veredicto.

### 2. El gate falla antes del fix y pasa después

La reproducción es un **experimento diferencial**, no una comprobación de que el árbol
está verde. En el worktree efímero, en el commit registrado como estado inicial de la
trayectoria:

- `gate` en el estado **pre-fix** debe salir **≠ 0**.
- `gate` en el estado **post-fix** debe salir **0**.

Si el gate ya pasaba antes del fix, la trayectoria no demuestra nada: no verificada.
Esta es la condición que más candidatas va a descartar, y es la que hace que el número
signifique algo.

### 3. Se aplicó la trayectoria **abstraída**, no el diff original

Re-aplicar el diff guardado sólo demuestra que git funciona. Lo que se verifica es el
**procedimiento**: se re-ejecuta la trayectoria abstraída (`abstraction`, tras
`valid_when`) contra el worktree, y se comprueba que llega a un estado donde el gate
pasa.

Si la re-ejecución necesita el diff literal para llegar al estado final, el
procedimiento no está bien abstraído: no verificada. Vuelve a `candidate` con el motivo
registrado.

### 4. Aislamiento: worktree efímero, destruido siempre

- Worktree git nuevo sobre el commit registrado.
- Se destruye pase, falle o explote.
- Sin red. Sin acceso fuera del worktree. Sin efectos sobre el repo del usuario.
- Timeout duro por gate. Un gate que cuelga es un gate fallado.

Un verify que puede modificar el árbol de trabajo del usuario es un bug de seguridad,
no un fallo de tests.

### 5. Se registran los tres campos de `verified`

`verified = {gate_id, passed_at, run_id}`, los tres obligatorios (invariante del
schema). `run_id` apunta al registro completo de la corrida: worktree, commit, comando,
exit codes pre y post, duración, stdout/stderr truncado y redactado.

Sin `run_id` no hay auditoría, y sin auditoría `/nightshift why` no puede responder.
El schema rechaza `verified` parcial, y rechaza `status: procedure` sin `verified`.

## Qué NO cuenta como reproducción

Se lista explícitamente para que no vuelva a discutirse en M5:

| No cuenta | Por qué |
|---|---|
| Un LLM juzgando que el fix "se ve correcto" | Es exactamente Auto Dream. Perdemos la capacidad D. |
| El gate pasando sólo después (sin fallar antes) | No distingue el fix de un árbol que ya estaba verde. |
| Re-aplicar el diff original | Verifica git, no el procedimiento. |
| Que la trayectoria "corra sin errores" | Correr no es pasar. |
| Similitud de embeddings con una trayectoria verificada | Similitud no es evidencia. |
| Verificación parcial ("2 de 3 pasos reproducen") | Binario. Parcial = `candidate`. |

## Consecuencias

**Aceptadas:**

- **Pocas trayectorias se verificarán.** Con estas cinco condiciones, la tasa esperada
  es baja. Es el diseño: `candidate` no es el estado de fallo, es el estado normal.
  Por eso §6.3 mantiene las candidatas inyectables con menor peso, en lugar de
  descartarlas.
- Tipos enteros de tarea son estructuralmente no verificables (diseño, refactors sin
  test, exploración). Se quedan en `candidate` de forma permanente y **eso está bien**.
- Verify es caro en tiempo y disco. Corre en la ventana nocturna, nunca en línea.
- Cada verify consume worktrees y CPU: el scheduler necesita un presupuesto por noche
  para no dejar la Air sin batería a mitad de corrida.

**Ganadas:**

- La distinción `procedure` / `candidate` es un hecho con `run_id`, no una etiqueta.
- M5 tiene un gate propio no circular: precisión de `procedure` > precisión de
  `candidate` en la re-corrida del benchmark. Si la verificación no separa mejor que
  no verificar, la verificación no sirve — y eso también es un resultado.

## Alternativas consideradas

1. **LLM-as-judge sobre el resultado.** Rechazada: elimina la capacidad D. Es la
   alternativa barata y es exactamente lo que ADR-001 dice que no hacemos.
2. **Verificar re-aplicando el diff.** Rechazada: verifica git (condición 3).
3. **Verificación gradual (score 0–1).** Rechazada: un score continuo invita a mover el
   corte después de ver los datos. Binario y auditable.
4. **Verificar en el repo real en vez de un worktree.** Rechazada por seguridad: un
   verify no puede tocar el árbol del usuario (condición 4).
5. **Ejecutar verify en línea, al cerrar la trayectoria.** Rechazada: viola §7.2
   (nightshift nunca bloquea una sesión) y haría inviable el presupuesto nocturno.

## Abierto para M5

- Presupuesto por noche (nº de verifies, tiempo máximo). → `LATER.md`
- Política de re-verificación cuando el repo avanza y el commit registrado queda viejo:
  ¿un `procedure` caduca? → `LATER.md`
