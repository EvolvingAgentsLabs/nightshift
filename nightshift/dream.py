"""Dream fase 1 — `consolidate` (M3-a, spec §6.1).

Sobre las trayectorias `closed` del período: agrupar por similitud estructural, extraer
el patrón (hipótesis → señal decisiva → fix), producir `abstraction` y `valid_when`,
enlazar contradicciones, y dejar el resultado en `candidate`.

Tres cosas que este módulo hace y conviene leer antes de tocarlo:

**El modelo corre local, o no corre.** Qwen por `subprocess`. Si no hay modelo local
disponible, `dream` falla y lo dice: no cae a una API remota (spec §2.2) ni a una
heurística que finja ser consolidación. Un `consolidate` que no consolidó sale distinto
de 0.

**Lo determinista no se le pregunta al modelo.** Agrupar, elegir representante y
detectar contradicciones son reglas fijas y auditables. Al modelo se le pide una sola
cosa — abstraer — porque es la única que no sabemos escribir como regla.

**La salida del modelo pasa por los mismos gates que la captura.** El esquema rechaza
paths en `abstraction.pattern` (spec §4.4), el redactor rechaza identificadores del repo
y el auditor de M1 rechaza fugas. Si el modelo produce algo que no valida, se reintenta
y si insiste se descarta el grupo: el bug es del prompt, no del esquema.
"""

from __future__ import annotations

import json
import re
import os
import shutil
import subprocess
import tempfile

from . import audit, config, context, store
from .redact import Redactor

DEFAULT_TIMEOUT = 180
MAX_STEPS_EN_PROMPT = 6
MAX_TRAYECTORIAS_POR_GRUPO = 4
MAX_CHARS_POR_PASO = 160
MAX_SIGNALS = 5
MAX_VALID_WHEN = 5
CANDIDATE_WEIGHT = 0.6   # `procedure` = 1.0; `candidate` < 1.0 (spec §6.3)
REINTENTOS = 2

# Respuesta legítima del modelo, no un error: estas trayectorias no comparten patrón.
SIN_PATRON = "el modelo dijo que no hay patrón común"
# Distinto de SIN_PATRON, y la diferencia importa: uno es "el modelo miró y no había
# patrón", el otro es "no se capturó nada que mirar". Confundirlos es exactamente cómo
# el bug de los campos del payload sobrevivió dos milestones (spec §5.9).
SIN_CONTENIDO = "la trayectoria no tiene ningún paso con contenido capturado"

# Un modelo que piensa en voz alta antes de responder. No es error: se descarta.
THINKING_RE = re.compile(r"<think(?:ing)?>.*?</think(?:ing)?>", re.S | re.I)
DONE_THINKING_RE = re.compile(r"^.*?\.\.\.done thinking\.\s*", re.S | re.I)

# ollama escribe secuencias de control en stdout aunque no haya terminal, y algunas caen
# dentro de los strings del JSON. Un carácter de control ahí hace fallar a `json.loads`,
# así que se limpian antes de parsear. Encontrado corriendo el modelo, no leyendo la doc.
ANSI_RE = re.compile(r"\x1b\[[0-9;?]*[ -/]*[@-~]")

# El caso feo: ollama re-acomoda las palabras al ancho de la terminal aunque stdout sea
# un pipe. Emite "…par" + ESC[3D (volvé 3) + ESC[K + "\npartido", o sea vuelve el cursor
# y reescribe la palabra en la línea siguiente. Borrar los escapes a secas deja el
# fragmento duplicado ("parpartido") y un salto de línea dentro de un string JSON, que es
# JSON inválido. Hay que *replicar* el movimiento del cursor, no ignorarlo.
CURSOR_BACK_RE = re.compile(r"\x1b\[(\d*)D")


class DreamError(RuntimeError):
    """Dream no pudo hacer su trabajo. Nunca se traga: sale distinto de 0."""


class ModelUnavailable(DreamError):
    pass


# ------------------------------------------------------------------- el modelo
BACKENDS = ("claude-code", "local")


def detect_command(cfg) -> list[str] | None:
    """Comando del modelo que consolida. Ver ADR-003.

    Dos backends, y el default es `claude-code`: el mismo agente que ya está instalado y
    autenticado, invocado por `subprocess` en modo no interactivo. El backend `local`
    (Qwen por ollama) sigue disponible y es el que hay que elegir cuando las trayectorias
    no pueden salir de la máquina.

    `model_command` en la config gana sobre todo: es la puerta para cualquier otro
    ejecutable que lea un prompt por stdin y escriba texto por stdout.
    """
    configured = cfg.get("model_command")
    if configured:
        return [str(part) for part in configured]

    backend = cfg.get("model_backend", "claude-code")
    if backend == "claude-code":
        return _claude_command(cfg)
    if backend == "auto":
        return _claude_command(cfg) or _ollama_command()
    return _ollama_command()


def _claude_command(cfg):
    """El agente que ya está instalado, en modo no interactivo.

    `--output-format json` devuelve un envoltorio con la respuesta en `result`; de
    desenvolverlo se encarga `extract_json`. El modelo concreto se deja sin fijar salvo
    que la config lo diga: elegirlo por su cuenta sería fijar una constante del
    experimento (PREREG §2).
    """
    claude = shutil.which("claude")
    if not claude:
        return None
    comando = [claude, "-p", "--output-format", "json"]
    if cfg.get("model_name"):
        comando += ["--model", str(cfg["model_name"])]
    return comando


def _ollama_command():
    """Qwen por ollama: el más chico ya descargado. Nunca baja nada solo.

    Un `dream` que se descarga 7 GB en la primera corrida no es autodetección, es una
    sorpresa.
    """
    ollama = shutil.which("ollama")
    if not ollama:
        return None
    try:
        out = subprocess.run([ollama, "list"], capture_output=True, text=True, timeout=20)
    except (OSError, subprocess.SubprocessError):
        return None
    if out.returncode != 0:
        return None

    qwens = []
    for line in out.stdout.splitlines()[1:]:
        name = line.split()[0] if line.split() else ""
        if "qwen" in name.lower():
            match = re.search(r"(\d+(?:\.\d+)?)b", name.lower().split(":")[-1])
            qwens.append((float(match.group(1)) if match else 999.0, name))
    if not qwens:
        return None
    qwens.sort()
    # `--think false` no cambia la respuesta, cambia cuánto tarda: 6s contra 56s con el
    # mismo modelo. En una ventana nocturna eso es la diferencia entre consolidar el
    # período entero y consolidar tres grupos.
    return [ollama, "run", qwens[0][1], "--format", "json", "--think", "false",
            "--nowordwrap"]


class LocalModel:
    """El modelo local detrás de `subprocess`. Sin HTTP, sin cliente, sin daemon."""

    def __init__(self, command, timeout=DEFAULT_TIMEOUT, home=None):
        self.command = [str(part) for part in command]
        self.timeout = timeout
        # Con qué `HOME` corre el hijo. Normalmente el que haya: hereda el del proceso.
        # Existe porque el backend por defecto es un **agente con credenciales propias**
        # (ADR-003), y sus credenciales viven en el HOME. Quien esté corriendo con un HOME
        # de mentira —el ensayo end-to-end, que lo usa para no instalar un timer de
        # verdad— le está sacando la sesión al modelo sin querer: `claude -p` devuelve
        # `is_error` y sale 1, con stderr vacío. Sandboxear el HOME sandboxea el login.
        self.home = home
        # Lo que llevamos gastado. Un backend local devuelve 0 y es la respuesta correcta;
        # uno que cobra por token devuelve lo que cobró. Consolidar dejó de ser gratis con
        # ADR-003, y una corrida nocturna cuyo costo nadie anotó no se puede justificar.
        self.total_cost = 0.0
        # Y los tokens, que es lo que una suscripción consume de verdad. El costo que
        # reporta el agente viene con `costBasis: "list"`: sirve para comparar corridas
        # entre sí, no para decir cuánto se pagó.
        self.total_input_tokens = 0
        self.total_output_tokens = 0

    @property
    def name(self) -> str:
        """El comando, sin la ruta absoluta del ejecutable.

        `shutil.which` devuelve algo como `/Users/alguien/.local/bin/claude`, y ese
        nombre se **persiste** en `consolidation_model`. El auditor lo encontró como
        `home_path`: una fuga que entró por la puerta de servicio, en un campo que nadie
        pensó como texto capturado porque lo escribe nightshift y no el usuario.

        El basename identifica igual —qué backend consolidó, con qué flags, con qué
        modelo— que es lo que PREREG §2 pide declarar. La ruta no agregaba nada.
        """
        if not self.command:
            return ""
        return " ".join([os.path.basename(self.command[0])] + list(self.command[1:]))

    def _run(self, command, prompt):
        # El hijo corre con un `NIGHTSHIFT_HOME` desechable. Si el ejecutable resulta ser
        # un agente con los hooks de nightshift cargados —que es exactamente el caso del
        # backend `claude-code`— sin esto la consolidación capturaría su propia sesión en
        # el store que está consolidando. Sin config en ese directorio, la captura ni
        # siquiera arranca (spec §8.1), así que el guard es el propio invariante.
        entorno = dict(os.environ)
        try:
            with tempfile.TemporaryDirectory(prefix="nightshift-model-") as tmp:
                entorno["NIGHTSHIFT_HOME"] = tmp
                if self.home:
                    entorno["HOME"] = self.home
                return subprocess.run(command, input=prompt, capture_output=True, text=True,
                                      timeout=self.timeout, env=entorno)
        except subprocess.TimeoutExpired:
            raise DreamError("el modelo local no respondió en %ds: %s"
                             % (self.timeout, self.name))
        except OSError as exc:
            raise ModelUnavailable("no se pudo ejecutar el modelo local (%s): %s"
                                   % (self.name, exc))

    def ask(self, prompt: str) -> str:
        out = self._run(self.command, prompt)
        if out.returncode != 0 and "unknown flag" in (out.stderr or "").lower():
            # Los flags de ollama cambian entre versiones. Si uno no existe, se cae a lo
            # que existe desde siempre en vez de reportar "no hay modelo": hay modelo.
            basico = [part for part in self.command
                      if part not in ("--think", "false", "--format", "json",
                                      "--hidethinking", "--nowordwrap")]
            out = self._run(basico, prompt)
        if out.returncode != 0:
            raise DreamError("el modelo local salió %d: %s"
                             % (out.returncode, (out.stderr or "").strip()[:300]))
        return out.stdout

    def _anotar_uso(self, salida):
        """Suma tokens y costo si el backend los reporta. El envoltorio del agente los trae.

        Los tokens son lo que consume una suscripción. El costo que acompaña viene a
        precio de lista (`costBasis: "list"`) y sirve como vara para comparar corridas
        entre sí — no es lo que se factura, y nada de lo que imprime el CLI lo presenta
        como si lo fuera.
        """
        envoltorio = extract_json(salida, _profundidad=3)   # sin desenvolver: el resumen
        if not isinstance(envoltorio, dict):
            return
        costo = envoltorio.get("total_cost_usd") or envoltorio.get("cost_usd")
        if isinstance(costo, (int, float)):
            self.total_cost += float(costo)
        for uso in (envoltorio.get("modelUsage") or {}).values():
            if not isinstance(uso, dict):
                continue
            for clave in ("inputTokens", "cacheReadInputTokens",
                          "cacheCreationInputTokens"):
                self.total_input_tokens += uso.get(clave) or 0
            self.total_output_tokens += uso.get("outputTokens") or 0

    def ask_json(self, prompt: str):
        salida = self.ask(prompt)
        self._anotar_uso(salida)
        # La ideación viaja como prosa antes del JSON. Se guarda acá y no se devuelve
        # para no romper la interfaz que usa el resto: un backend que no idea deja
        # `last_ideation` en None y todo sigue igual.
        self.last_ideation = extract_ideation(salida)   # compatibilidad: marcas viejas
        data = extract_json(salida)
        if data is None:
            raise DreamError("el modelo no devolvió JSON parseable")
        return data


IDEACION_RE = re.compile(r"<ideacion>(.*?)</ideacion>", re.S | re.I)


def extract_ideation(salida: str):
    """El boceto entre las marcas, si el modelo lo escribió.

    El envoltorio del agente trae la respuesta como string JSON, así que los saltos de
    línea llegan escapados: sin deshacerlos la ideación se guarda con `\n` literales
    adentro. No es cosmético — ese texto se inyecta.
    """
    if not salida:
        return None
    match = IDEACION_RE.search(salida.replace("\\n", "\n"))
    if not match:
        return None
    texto = " ".join(match.group(1).split())
    return texto or None


def undo_wrapping(text: str) -> str:
    """Deshace el re-acomodo de palabras de ollama replicando el cursor.

    `ESC[nD` borra los n caracteres anteriores, porque lo que venga después los
    sobreescribe; y el salto de línea inmediatamente posterior es del wrapping, no del
    contenido. Se usa `--nowordwrap` cuando la versión de ollama lo soporta; esto es la
    red para cuando no.
    """
    out = []
    i = 0
    while i < len(text):
        match = CURSOR_BACK_RE.match(text, i)
        if match:
            back = int(match.group(1) or "1")
            del out[len(out) - min(back, len(out)):]
            i = match.end()
            while i < len(text) and ANSI_RE.match(text, i):
                i = ANSI_RE.match(text, i).end()
            if i < len(text) and text[i] == "\n":
                i += 1
            continue
        out.append(text[i])
        i += 1
    return "".join(out)


def extract_json(text: str, _profundidad=0):
    """Primer objeto JSON balanceado del texto. `None` si no hay ninguno.

    Un agente en modo no interactivo devuelve un **envoltorio** —`{"result": "...",
    "num_turns": 1, ...}`— con la respuesta adentro, en texto. Si el objeto que sale es
    ese envoltorio, se vuelve a buscar dentro de `result`: quedarse con el envoltorio
    sería leer la factura en vez de la respuesta.
    """
    if not text:
        return None
    text = undo_wrapping(text)
    text = ANSI_RE.sub("", text)
    text = THINKING_RE.sub("", text)
    if "done thinking" in text.lower():
        text = DONE_THINKING_RE.sub("", text)
    start = text.find("{")
    while start != -1:
        depth = 0
        in_string = False
        escaped = False
        for i in range(start, len(text)):
            char = text[i]
            if in_string:
                if escaped:
                    escaped = False
                elif char == "\\":
                    escaped = True
                elif char == '"':
                    in_string = False
                continue
            if char == '"':
                in_string = True
            elif char == "{":
                depth += 1
            elif char == "}":
                depth -= 1
                if depth == 0:
                    try:
                        dato = json.loads(text[start:i + 1])
                    except ValueError:
                        break
                    if (isinstance(dato, dict) and _profundidad < 3
                            and "pattern" not in dato
                            and isinstance(dato.get("result"), str)):
                        adentro = extract_json(dato["result"], _profundidad + 1)
                        if adentro is not None:
                            return adentro
                    return dato
        start = text.find("{", start + 1)
    return None


# ------------------------------------------------------- agrupación estructural
def structural_key(task_type, steps):
    """Clave de agrupación: el tipo de tarea. Determinista y explicable.

    La primera versión usaba tipo de tarea **más** la firma exacta de herramientas y
    clases de paso. Corriéndola contra el set fixture dejaba grupos de uno: dos
    trayectorias del mismo bug — una que falló y una que lo arregló — caían en grupos
    distintos porque una tenía un `tool_failure` y la otra no. Y un grupo de uno no puede
    tener contradicciones, que es justo lo que la capacidad B necesita ver.

    La forma de la trayectoria no se pierde: entra en el prompt, que es donde importa.
    Agrupar más fino que esto necesita volumen real de trayectorias, no una intuición.
    """
    return (task_type,)


def groups(conn, *, lookback_days=7, limit=200):
    """Trayectorias `closed` del período, agrupadas por forma. Orden estable."""
    cutoff = store.hours_ago(24 * lookback_days)
    rows = conn.execute(
        "SELECT * FROM trajectories WHERE status = 'closed' AND created_at >= ?"
        " ORDER BY created_at, rowid LIMIT ?", (cutoff, limit)).fetchall()
    buckets = {}
    for row in rows:
        steps = store.steps_of(conn, row["id"])
        if not steps:
            continue
        buckets.setdefault(structural_key(row["task_type"], steps), []).append(row)
    return [buckets[key] for key in sorted(buckets)]


# ------------------------------------------------------------------- capítulos
#
# **La sesión es la unidad de captura y la trayectoria es la unidad de consolidación, así
# que hasta acá eran la misma cosa** — y cuanto más productivo es el día, menos
# consolidable queda: quince tandas de trabajo, cada una con su rama y su merge, se
# guardan como una sola trayectoria que no se parece a nada (`LATER.md`).
#
# Segmentar sola una sesión larga es el problema difícil, y sigue sin resolverse. Lo que
# esto hace es **esquivarlo**: la persona que está trabajando sabe cuándo terminó un
# capítulo —un `make check` en verde, un merge— y lo dice. El detector de bordes es ella.
#
# `Stop` no cierra la trayectoria a propósito (spec §5.6): dispara por turno, y cerrar ahí
# partiría la sesión en dos sin que nadie lo pidiera. Sellar a demanda hace exactamente
# eso, la partición, pero **porque alguien la pidió en el borde que eligió**. Esa es toda
# la diferencia, y es la que la vuelve legítima.
#
# Que la sesión siga capturando después no es una esperanza: `hook._ensure_trajectory`
# busca la trayectoria `open` de la sesión y, si no hay, **abre una nueva**. Sellar deja a
# la sesión sin trayectoria abierta exactamente hasta el próximo evento de hook. Hay un
# test que lo fija, porque si eso dejara de ser cierto la captura se apagaría en silencio
# a mitad de sesión, que es el peor modo de falla de este proyecto.


# Queda en `outcome_evidence`. Una trayectoria sellada a mano y una cerrada por fin de
# sesión no son la misma clase de dato, y el store tiene que poder distinguirlas sin
# adivinar.
MARCA_DE_CAPITULO = "capítulo sellado a demanda, sesión en curso"


def open_chapters(conn, repo_fingerprint=None, limit=10):
    """Trayectorias `open`, la de actividad más reciente primero.

    El CLI **no sabe el `session_id`**: `CLAUDE_PLUGIN_DATA` llega a los hooks y no al
    Bash tool, y por eso el store se fija en `~/.nightshift` (HANDOFF §3). Así que el
    capítulo en curso se identifica por repo y actividad, no por sesión — y cuando hay más
    de uno, quien llama tiene que elegir en vez de adivinar.
    """
    sql = ("SELECT t.*,"
           " COALESCE((SELECT MAX(s.at) FROM steps s WHERE s.trajectory_id = t.id),"
           "          t.created_at) AS last_at,"
           " (SELECT COUNT(*) FROM steps s WHERE s.trajectory_id = t.id) AS n_steps"
           " FROM trajectories t WHERE t.status = 'open'")
    params = []
    if repo_fingerprint:
        sql += " AND t.repo_fingerprint = ?"
        params.append(repo_fingerprint)
    sql += " ORDER BY last_at DESC, t.rowid DESC LIMIT ?"
    params.append(limit)
    return conn.execute(sql, params).fetchall()


def seal_chapter(conn, row):
    """Cierra una trayectoria `open` sin terminar la sesión. Devuelve `(estado, result)`.

    El desenlace se infiere con la misma regla que usa `SessionEnd` — no hay una segunda
    heurística para lo mismo. La evidencia dice que el borde lo puso una persona, porque
    una trayectoria sellada a mano y una cerrada por fin de sesión no son la misma clase
    de dato y el store tiene que poder distinguirlas.
    """
    from .hook import _infer_outcome        # tardío: `hook` no importa `dream`

    result, evidence = _infer_outcome(conn, row["id"])
    # El marcador va **siempre**, no sólo cuando no hay otra evidencia. La primera versión
    # ponía `evidence or MARCA`, y en la primera corrida real sobre este repo el desenlace
    # salió `tests_passed` con evidencia propia: el marcador desapareció exactamente en el
    # caso informativo, que es donde más importa poder distinguir un borde puesto a mano de
    # uno puesto por `SessionEnd`. El test que había cubría sólo la rama sin evidencia y
    # pasaba en verde — el mismo modo de falla que este repo ya documentó dos veces.
    evidence = "%s · %s" % (evidence, MARCA_DE_CAPITULO) if evidence else MARCA_DE_CAPITULO
    estado = store.close_trajectory(conn, row["id"], result=result, evidence=evidence)
    return estado, result


OUTCOME_RANK = {"tests_passed": 3, "unknown": 2, "user_corrected": 1}


def representative(group):
    """La trayectoria que se va a promover: el mejor desenlace, y entre iguales la más nueva."""
    return sorted(group, key=lambda r: (OUTCOME_RANK.get(r["outcome_result"], 0),
                                        r["created_at"]))[-1]


def contradicted_by(conn, group, winner):
    """Miembros anteriores que el representante contradice.

    Contradicción es una señal registrada, no una opinión del modelo: el usuario corrigió
    un paso, o el desenlace fue `user_corrected`. La vieja **no se borra** — pasa a
    `superseded` enlazada a la nueva (capacidad B, spec §4.2).
    """
    out = []
    for row in group:
        if row["id"] == winner["id"] or row["created_at"] > winner["created_at"]:
            continue
        if row["outcome_result"] == "user_corrected" or any(
                step["contradicted"] for step in store.steps_of(conn, row["id"])):
            out.append(row)
    return out


# ------------------------------------------------------------------- el prompt
def texto_del_paso(step) -> str:
    """Lo que ese paso tiene para decir. Vacío si no capturó nada."""
    return ((step["error_message"] or "") or (step["result_summary"] or "")).strip()


# Orden en que se llenan los MAX_STEPS_EN_PROMPT lugares del prompt. Un paso sin texto
# no compite por un lugar: no lo tiene.
def _prioridad(step) -> int:
    if step["kind"] == "tool_failure":
        return 0                      # el momento en que el problema se manifestó
    if step["contradicted"]:
        return 1                      # "no, eso está mal": la señal negativa más barata
    if step["decisive"]:
        return 2
    return 3


# ------------------------------------------------------- la cadena, con eslabones
#
# El README y la spec afirman una cadena —`hipótesis → comando → error → corrección →
# señal decisiva → fix`— que hasta acá **no era una estructura de datos**: los pasos eran
# una lista plana con dos banderas, y la cadena estaba implícita en el orden, que es la
# forma más débil de tenerla. `why` no podía decir qué corrección arregló qué error.
#
# Se **deriva** de lo persistido en vez de guardarse como banderas nuevas, y a propósito:
# una propiedad calculada en la captura no sobrevive a un cambio de criterio ni se puede
# recalcular hacia atrás sobre lo que ya está en el store. Los ingredientes —`kind`,
# `contradicted`, `decisive`, el orden y el comando— ya están todos guardados.
ESLABONES = ("fallo", "correccion", "decisiva", "fix")


def cadena(steps):
    """Los eslabones causales de una trayectoria. Determinista y auditable.

    Devuelve una lista de `{"eslabon", "idx", "corrects", "texto"}`. `corrects` es lo que
    faltaba: **qué paso arregla este paso**, y sólo lo tiene la corrección, porque es el
    único enlace que la captura registra de verdad (el usuario contradijo el paso
    anterior). Inventar los otros enlaces sería exactamente la clase de afirmación sin
    origen que este proyecto no acepta.
    """
    enlaces = []
    pendiente = None            # el idx contradicho que todavía no tiene quien lo corrija
    for step in steps:
        idx = int(step["idx"])
        texto = texto_del_paso(step)
        if step["contradicted"]:
            pendiente = idx
            continue
        if step["kind"] == "tool_failure":
            enlaces.append({"eslabon": "fallo", "idx": idx, "corrects": None, "texto": texto})
        elif pendiente is not None and step["kind"] in ("tool_use", "tool_failure"):
            # El primer paso de herramienta después de una contradicción es la corrección.
            enlaces.append({"eslabon": "correccion", "idx": idx, "corrects": pendiente,
                            "texto": texto})
            pendiente = None
        elif step["decisive"]:
            enlaces.append({"eslabon": "decisiva", "idx": idx, "corrects": None,
                            "texto": texto})
    # El fix es el último paso que **hizo** algo, no el que lo miró: el sello del turno y
    # las lecturas del repo no arreglan nada.
    for step in reversed(steps):
        if step["kind"] == "observation" or es_lectura(step):
            continue
        if texto_del_paso(step):
            enlaces.append({"eslabon": "fix", "idx": int(step["idx"]), "corrects": None,
                            "texto": texto_del_paso(step)})
            break
    return sorted(enlaces, key=lambda e: (e["idx"], ESLABONES.index(e["eslabon"])))


# ----------------------------------------------------------- dónde corta un capítulo
#
# Detectar el borde, que `sleep` resolvió pidiéndoselo a una persona (`LATER.md`).
#
# **Sugiere, no corta.** La diferencia no es timidez: nadie midió todavía si los bordes
# que propone esta heurística producen candidatas mejores que un día entero, y sellar solo
# convertiría una conjetura sobre la segmentación en un hecho irreversible sobre el store.
# Con `sleep` andando ese número **se puede medir**, y medirlo es lo que habilita el
# siguiente paso.
def suggest_chapters(conn, trajectory_id, *, min_pasos=5):
    """Dónde parece terminar un capítulo. Devuelve `[{"idx", "motivo"}]`.

    El corte va donde el trabajo **cerró algo**: un comando de test que pasó, o un commit.
    Es la misma señal que el proyecto ya usa para el desenlace (`_es_comando_de_test`), y
    no una intuición nueva.
    """
    from .hook import _es_comando_de_test

    steps = store.steps_of(conn, trajectory_id)
    bordes, ultimo = [], -1
    for step in steps:
        idx = int(step["idx"])
        if step["kind"] == "tool_failure":
            continue                          # un gate en rojo no cierra nada
        motivo = None
        if _es_comando_de_test(step):
            motivo = "un comando de test que no falló"
        else:
            try:
                comando = str((json.loads(step["args_json"] or "{}") or {}).get("command", ""))
            except (TypeError, ValueError):
                comando = ""
            if re.search(r"(?:^|[;&|]|\n)\s*git\s+commit\b", comando):
                motivo = "un commit"
        if motivo and idx - ultimo >= min_pasos:
            bordes.append({"idx": idx, "motivo": motivo})
            ultimo = idx
    return bordes


def es_lectura(step) -> bool:
    """¿Este paso **leyó** el repositorio, en vez de ejercitarlo? (plan §7, F2)

    Determinista, del comando guardado, igual que `_es_comando_de_test` y por el mismo
    motivo: una bandera calculada en la captura no sobrevive a un cambio de criterio, y
    esto se puede recalcular sobre lo que ya está en el store.

    Un fallo nunca es lectura, aunque el comando sea un `grep`: que algo haya salido
    distinto de cero **es** una observación de esta sesión.
    """
    if step["kind"] in ("tool_failure", "observation") or step["contradicted"]:
        return False
    if context.normalize_tool(step["tool_native"]) in context.READ_TOOLS:
        return True
    if step["tool"] in context.READ_TOOLS:
        return True
    if step["tool"] != "run_shell":
        return False
    try:
        args = json.loads(step["args_json"] or "{}")
    except (TypeError, ValueError):
        return False
    if not isinstance(args, dict):
        return False
    comando = str(args.get("command", ""))
    if context.TEST_CMD_RE.search(comando):
        return False        # correr los tests es ejercitar, no leer
    return bool(context.READ_CMD_RE.search(comando))


def pasos_para_el_prompt(steps):
    """Los pasos que dream ve de una trayectoria: los que tienen algo escrito.

    Esto fue un bug de verdad, medido el 2026-08-27 sobre el store real. Una trayectoria
    de 400 pasos con 177 de contenido llegaba al modelo como **seis líneas vacías**, y el
    modelo respondía —correctamente— que no había patrón. La selección era "los decisivos
    primero", y `decisive` marca el 38% de los pasos sin exigirles contenido, así que la
    ventana caía entera sobre pasos vacíos mientras 177 con contenido no se miraban.

    Un paso sin texto no es evidencia débil: es la ausencia de evidencia, y ocupa un lugar
    que sí tiene quien lo use.
    """
    con_texto = [s for s in steps if texto_del_paso(s)]
    con_texto.sort(key=lambda s: (_prioridad(s), s["idx"]))
    elegidos = con_texto[:MAX_STEPS_EN_PROMPT]
    return sorted(elegidos, key=lambda s: s["idx"])


def indices_de_observacion(conn, rows) -> set:
    """Índices de los pasos que observan algo de esta sesión, en todo el grupo.

    Todo lo que no sea lectura del repositorio: fallos, tests, correcciones, ediciones,
    el sello del turno. Es el conjunto contra el que se ancla `hypothesis_step`.
    """
    indices = set()
    for row in rows:
        for step in store.steps_of(conn, row["id"]):
            if not es_lectura(step):
                indices.add(int(step["idx"]))
    return indices


def tiene_contenido(conn, row) -> bool:
    """¿Esta trayectoria tiene algo que abstraer, o es una silueta?"""
    return any(texto_del_paso(s) for s in store.steps_of(conn, row["id"]))


def describe(conn, row) -> str:
    steps = store.steps_of(conn, row["id"])
    shown = pasos_para_el_prompt(steps)
    lines = ["- trayectoria `%s` · tipo `%s` · desenlace `%s`"
             % (row["id"][:8], row["task_type"], row["outcome_result"] or "unknown")]
    if not shown:
        lines.append("  - (sin ningún paso con contenido capturado)")
        return "\n".join(lines)
    for step in shown:
        detail = texto_del_paso(step)[:MAX_CHARS_POR_PASO]
        # Una lectura va etiquetada. No es un adorno: sin la etiqueta, la salida de un
        # `grep` llega al modelo con el mismo rango que un fallo, y el modelo la usa
        # como observación sobre este trabajo — que es exactamente lo que produjo la
        # candidata falsa del 2026-08-28.
        etiqueta = " LECTURA-DEL-REPO" if es_lectura(step) else (
            " DECISIVO" if step["decisive"] else "")
        lines.append("  - [%d] %s%s (`%s`): %s"
                     % (step["idx"], step["kind"], etiqueta, step["tool"] or "—", detail))
    return "\n".join(lines)


# El bloque `ideate`, delante del prompt de consolidación. Ver ADR-004.
#
# La hipótesis: **el dibujo de un mecanismo es invariante entre síntomas de un modo que
# la prosa no lo es.** Diez fallas con una causa compartida se cuentan con diez prosas
# distintas y —si vale— con el mismo dibujo. Abstraer desde el dibujo tendría que dar un
# patrón que transfiere a un síntoma que no se vio.
#
# La segunda mitad es la proyección: desde el dibujo, anticipar en qué OTRAS formas se
# va a manifestar el mismo mecanismo. Eso es lo que convierte a dream en algo que mira
# para adelante y no sólo para atrás — y es también lo más fácil de convertir en
# fabricación, así que lo proyectado se guarda, se pesa y se muestra SIEMPRE separado de
# lo observado.
IDEATE_PREFIX = """Antes de responder, IDEÁ. No razones todavía: buscá la imagen.

Hay explicaciones que sólo se entienden cuando alguien las dibuja **bien**, y el dibujo
correcto no agrega información: saca la que sobra.

- **La transformada discreta de Fourier** no es una sumatoria con exponenciales: es
  enrollar la señal alrededor de un círculo a cada velocidad y mirar dónde queda el centro
  de masa. Si la señal tiene esa frecuencia adentro, el centro se corre del origen; si no,
  se queda ahí. Todo lo demás es contabilidad.
- **La convolución** es dar vuelta una de las dos, deslizarla sobre la otra, y anotar
  cuánto se solapan en cada posición. La curva que traza ese solapamiento es el resultado.
- **Una integral** es una aplicación que acumula área: rectángulos que se suman bajo la
  curva y se afinan hasta que el escalón deja de notarse.
- **La transformada Z** es una superficie sobre el plano: los polos son postes que la
  levantan, los ceros la clavan al piso, y la respuesta en frecuencia es la altura del
  terreno cuando caminás el círculo unidad.

Buscá **la imagen más corta que vuelve obvio el invariante** para el mecanismo que falla
acá. Si el dibujo es el correcto, el síntoma pasa a ser una consecuencia evidente en vez
de un dato suelto.

El dibujo va en dos partes, y las dos son obligatorias:

**1. `diagram` — un diagrama Mermaid.** Un diagrama es dibujo y texto a la vez: se lee y
se renderiza. Elegí el tipo según lo que estés mostrando — `flowchart` para un recorrido
donde algo se transforma, `sequenceDiagram` para capas que se hablan y se malentienden,
`stateDiagram-v2` para algo que cambia de estado sin que nadie lo mire. Poné en el
diagrama **lo que se conserva y dónde se pierde**: si hay un nodo donde el objeto cambia
de forma sin que ninguna etapa se queje, ese nodo es el punto del dibujo. Etiquetá las
aristas con qué viaja por ellas. Diez nodos como mucho: un diagrama que no entra de un
vistazo no es un dibujo, es un plano.

**2. `mechanism` — dos a cuatro oraciones** que digan lo que el diagrama no puede decir
solo: qué magnitud se conserva a lo largo de todo el recorrido, cuál se pierde sin que
nadie se queje, y en qué cuadro exacto se pierde. Es la pregunta que enseña la DFT: no
importa cada muestra, importa adónde va el centro de masa. Si el mecanismo ya tiene una
imagen canónica en otro dominio —una señal deformada por un filtro, dos llaves que abren
la misma cerradura, un cambio de coordenadas que hace desaparecer un término— nombrala:
esa analogía es el puente hacia todo lo que ya se sabe de ese dominio.

No repitas en `mechanism` lo que ya está en el diagrama. Entre los dos tiene que quedar el
dibujo completo, sin decir dos veces lo mismo.

Y del dibujo, PROYECTÁ: en qué otras formas se va a manifestar este mismo mecanismo, que
en estas trayectorias no se vieron. Con la imagen correcta esto no es adivinar — es leer
del diagrama qué otros caminos existen. Un síntoma proyectado es igual una conjetura, no
una observación, y se va a guardar y mostrar como tal. Si el dibujo no implica nada más,
no proyectes.

Devolvé `diagram` y `mechanism` como campos del JSON, junto con el resto.

---

"""

# ---------------------------------------------- el segundo modo: la escena física
#
# ADR-007. El brazo de arriba pide un diagrama Mermaid, y `experimentos/07` lo midió
# contra un conjunto retenido: engancha un síntoma más que el control y lo paga con un
# prompt ajeno (H17, `FAIL`). La objeción es sobre el **medio**, no sobre idear: un
# flowchart es topología —cajas y flechas— y para el modelo sigue siendo el mismo campo
# semántico del código. Cajas genéricas se parecen a demasiadas cosas.
#
# Este modo cambia el medio: una **escena física** con mecánica —peso, presión, algo que
# se derrama— y un **logograma**, dos a cuatro palabras que nombran el mecanismo entero
# como lo hace un pictograma. La apuesta es que la mecánica transporta a un síntoma que
# no se vio de un modo que la topología no.
#
# **No es el default y no se cambia por decreto.** Reemplazar un medio que pasa los gates
# por otro sin medir sería el mismo error que prender el primero con n=1. Se elige con
# `--ideacion fisica`, y lo que decida es la medición.
IDEATE_PREFIX_FISICO = """Antes de responder, IDEÁ. Y antes de idear, MIRÁ: todavía no
pienses en código.

Traducí lo que pasó a una escena del mundo físico. Una máquina con partes que se mueven,
un fluido que va por caños, cajas que viajan por una cinta, un tamiz, una cerradura, una
balanza, un molde. Con peso, con presión, con algo que se conserva y algo que se derrama.
La escena tiene que poder contársela a alguien que no programó nunca, y que igual entienda
dónde se rompe.

Por qué así y no como diagrama: un diagrama de cajas y flechas es **topología**, y la
topología se parece a todo. Una escena física tiene **mecánica** —qué empuja a qué, qué
pesa, qué no entra por dónde, qué se cae cuando nadie mira— y es esa mecánica la que se
transporta a un síntoma que no viste.

**1. `physical_scene` — la escena, en tres a seis oraciones.** Qué viaja, qué lo
transforma, en qué punto exacto algo se pierde **sin que ninguna etapa se queje**, y por
qué el que mira desde afuera no lo nota hasta mucho después. Nombrá objetos, no conceptos:
una válvula, un sello, una cinta, un contrapeso.

**No puede aparecer ni una sola palabra del mundo del software.** Ni archivo, ni función,
ni test, ni error, ni el nombre de ninguna herramienta. Si necesitás una, la traducción no
se hizo: escribiste la misma explicación de siempre con un título nuevo. Eso se rechaza,
igual que se rechaza una fuga.

**2. Ahora sí, RAZONÁ — y razoná sobre la escena, no sobre el código.** Escribí ese
razonamiento antes del JSON si te sirve: se descarta. De la **mecánica** salen las
proyecciones, y la pregunta no es "qué otro problema puede haber" sino **qué más tiene que
pasar en una máquina construida así**. Eso es correr la cadena para adelante.

**3. `logogram` — de dos a cuatro palabras.** Comprimí el mecanismo entero en un signo,
como un pictograma: no describe la escena, la **nombra**. "sello sin contenido", "válvula
sin retorno", "espejo opaco", "contrapeso ausente". No es un título lindo: es el nombre con
el que esta memoria se va a reconocer de un vistazo. Nunca nombres una herramienta.

**4. `mechanism` — dos a cuatro oraciones** que mapean la escena de vuelta al sistema: qué
magnitud se conserva a lo largo del recorrido, cuál se pierde sin que nadie se queje, y en
qué cuadro exacto se pierde.

`diagram` va en null: en este modo el dibujo es la escena.

Y de la escena, PROYECTÁ: en qué otras formas se va a manifestar este mismo mecanismo, que
en estas trayectorias no se vieron. Con la escena correcta esto no es adivinar — es leer de
la mecánica qué otra cosa tiene que romperse. Un síntoma proyectado es igual una conjetura,
no una observación, y se va a guardar y mostrar como tal. Si la escena no implica nada más,
no proyectes.

Devolvé `physical_scene`, `logogram` y `mechanism` como campos del JSON, junto con el resto.

---

"""

# Los dos medios de idear. **Ninguno apaga la ideación**: `fisica` es otro dibujo, no una
# salida (H14). Un modo que no esté acá no existe.
#
# El default es `fisica` desde la enmienda 0.3.10, **por decisión de Matías del
# 2026-08-28 y no por medición**: H23 —¿la escena transfiere donde el diagrama no?— sigue
# sin un veredicto válido, y el ADR-007 lo registra así. `mermaid` sigue disponible con
# `--ideacion mermaid`, y es lo que permite volver a comparar.
MODOS_DE_IDEACION = ("mermaid", "fisica")
MODO_DE_IDEACION = "fisica"

PREFIJOS_DE_IDEACION = {"mermaid": IDEATE_PREFIX, "fisica": IDEATE_PREFIX_FISICO}


PROMPT = """Sos el consolidador de nightshift. Te doy trayectorias de trabajo ya
capturadas y redactadas: pasos de herramientas, fallos y señales. Tu única tarea es
abstraer el patrón que comparten.

Devolvé SÓLO un objeto JSON, sin texto alrededor, con esta forma exacta:

{
  "pattern": "forma del problema y del fix, en 1-3 oraciones",
  "hypothesis": "la hipótesis con la que arrancó el trabajo, en una oración, o null",
  "hypothesis_step": 3,
  "signals": ["señal observable que indica que este patrón aplica"],
  "decisive_signal": "la observación que volvió concluyente el diagnóstico",
  "valid_when": ["precondición bajo la que este procedimiento aplica"],
  "projected_signals": ["síntoma que este mecanismo produciría y que NADIE observó"],
  "diagram": "el dibujo del mecanismo, en el medio que te hayan pedido arriba, o null",
  "mechanism": "qué se conserva y qué se pierde, sólo si te pidieron idear"
}

Reglas duras. Una respuesta que las rompa se descarta:

- `pattern` describe la ESTRUCTURA, no el caso. Nada de rutas de archivo, nombres de
  repositorio, de paquete, de archivo, de rama, ni dominios. Ni `/algo/`, ni `~/`, ni
  `../`. Si necesitás nombrar un archivo, decí "el módulo afectado".
- Todo en español, sin markdown, sin backticks dentro de los strings.
- `signals` y `valid_when`: como mucho 5 elementos cada uno, oraciones cortas.
- Cada paso viene con su índice entre corchetes. Los marcados **LECTURA-DEL-REPO** son el
  repositorio hablando de sí mismo —salida de `grep`, de `cat`, de `git log`— y **no son
  observaciones sobre este trabajo**: un comentario del código puede describir un diseño
  viejo, ajeno o ya revertido. Sirven de contexto y nunca de evidencia. Si el único
  respaldo de algo que ibas a escribir es una LECTURA-DEL-REPO, no lo escribas.
- `hypothesis` es **el primer eslabón de la cadena causal**: con qué se creyó que era el
  problema al empezar, aunque después resultara equivocada. Va con `hypothesis_step`, el
  índice del paso **que no sea LECTURA-DEL-REPO** del que la inferiste. Si no podés
  señalar uno, poné las dos en null: una hipótesis obvia inventada es peor que ninguna.
- `signals` es lo que SE VIO en estas trayectorias. `projected_signals` es lo que el
  mismo mecanismo produciría en otra parte y no se vio. Nunca pongas en `signals` algo
  que no esté en los pasos: la diferencia entre observar y anticipar es la única que
  hace que esto sea memoria y no adivinación. Si no te pidieron idear, dejá
  `projected_signals` vacío.
- **`signals`, `valid_when`, `projected_signals` y `logogram` son la única superficie
  contra la que se busca.** Cuando alguien abra la próxima sesión y describa lo que le
  está pasando, el retrieval compara sus palabras contra esos campos y
  **nunca contra `pattern`**. Así que ahí no va tu mejor oración de diseño: va el
  **síntoma, como lo diría quien lo sufre** antes de saber la causa —"la corrida termina
  en verde y no procesó ni un caso", no "una aserción cuantifica sobre una colección
  vacía". `pattern` explica; `signals` se encuentra. El logograma se busca con el piso
  más alto: sólo engancha cuando el prompt trae casi el signo entero, así que sus dos a
  cuatro palabras tienen que ser las que alguien usaría de verdad.
- **Nombrá el mecanismo, no la herramienta.** Un síntoma escrito alrededor de un nombre
  propio de herramienta engancha con cualquier otro problema de esa herramienta: decir
  "el linter" trae también al que se queja de un import sin usar. Decí qué hace la cosa
  —"el chequeo", "el resumen", "la corrida"— y el enganche se apoya en el mecanismo.
- **Abstenerse es una respuesta, y es la que más cuesta dar.** Si estas trayectorias no
  comparten un mecanismo, devolvé {"pattern": null} y nada más. Medido el 2026-08-28:
  contra tres trabajos sin absolutamente nada en común —un margen de CSS, un índice
  faltante en una base, una coma de más en un JSON— este prompt encontró un patrón las
  **tres de tres** veces que se le preguntó. Lo que encontró era cierto y vacío: cosas que
  le pasan a cualquier software. Antes de escribir un patrón, exigite poder señalar el
  **paso concreto de cada trayectoria** donde el mismo mecanismo actúa; si para una sola de
  ellas tenés que argumentar, no hay patrón. Compartir género —"son todos bugs", "en todos
  el error aparece lejos de la causa"— no es compartir mecanismo.

Trayectorias:

%s
"""

RETRY_SUFFIX = """

Tu respuesta anterior fue RECHAZADA por estos motivos:
%s

No expliques el rechazo. Devolvé sólo el JSON corregido.
"""


CONTRAST_PROMPT = """Sos el consolidador de nightshift. Te doy DOS trayectorias sobre el
mismo problema: una que se descartó y la que la reemplazó. Tu tarea no es abstraer
ninguna de las dos — es abstraer **la diferencia**.

Una alternativa descartada sin su precondición es ruido. Con ella es conocimiento: dentro
de tres semanas alguien va a proponer otra vez el camino descartado, y lo único que puede
evitarlo es saber qué se probó, qué pasó, y bajo qué condición esa opción **sí** era la
correcta.

Devolvé SÓLO un objeto JSON, sin texto alrededor:

{
  "changed": "qué cambió entre una y otra, en términos estructurales, 1-2 oraciones",
  "bought": "qué compró ese cambio: qué falla deja de ser posible, 1-2 oraciones",
  "old_valid_when": ["condición bajo la cual la opción DESCARTADA seguía siendo correcta"],
  "cost": "qué se pagó por el cambio, o null si no se pagó nada"
}

Reglas duras. Una respuesta que las rompa se descarta:

- Nada de rutas de archivo, nombres de repositorio, de paquete, de rama, ni dominios.
  Ni `/algo/`, ni `~/`, ni `../`. Si necesitás nombrar un archivo, decí "el módulo
  afectado".
- `bought` dice qué **deja de ser posible**, no qué quedó más lindo. Si el cambio no
  elimina ninguna falla, decilo: es la respuesta correcta y es información.
- `old_valid_when` es lo más valioso y lo más fácil de arruinar. No escribas "cuando no
  importa la correctitud" ni condiciones que nunca se dan: eso es una forma elegante de
  decir "nunca", y entonces poné una lista vacía. Escribilo sólo si hay un régimen real
  —otro tamaño, otra restricción, otro orden de magnitud— donde la vieja gana.
- Todo en español, sin markdown, sin backticks dentro de los strings.

Trayectoria DESCARTADA:

%s

Trayectoria que la REEMPLAZÓ:

%s
"""


# El contraste consume `changed`/`bought`/`cost`/`old_valid_when` y nada más. La aspereza
# se midió el 2026-08-28: con el prefijo de ideación a secas, el modelo devolvía también
# la escena, el logograma y el diagrama, que `validate_contrast` descarta en silencio y se
# pagan como tokens de salida. Esta línea es el recorte (enmienda 0.3.10, decidido por
# Matías): idear sí —el contraste se piensa igual—, devolver el dibujo no.
CONTRAST_TRIM = """

Esto es un CONTRASTE, no una consolidación: usá la escena para pensar y NO la devuelvas.
El JSON lleva SOLO `changed`, `bought`, `cost` y `old_valid_when` — nada de
`physical_scene`, `logogram`, `diagram`, `mechanism` ni `projected_signals`.

---

"""


def build_contrast_prompt(conn, old_row, new_row, *, ideate=True,
                          modo=MODO_DE_IDEACION) -> str:
    """El contraste también se idea. `ideate=False` existe sólo para el brazo de control
    de `experimentos/ideate.py`: en el plugin no hay ninguna ruta que lo apague.

    En modo `fisica` el prefijo lleva el recorte de `CONTRAST_TRIM`: la escena se usa
    para pensar y no se devuelve — los campos visuales de la alternativa descartada eran
    tokens pagados que `validate_contrast` tiraba (medido el 2026-08-28, LATER.md)."""
    cuerpo = CONTRAST_PROMPT % (describe(conn, old_row), describe(conn, new_row))
    if not ideate:
        return cuerpo
    prefijo = PREFIJOS_DE_IDEACION[modo]
    if modo == "fisica":
        prefijo = prefijo.rstrip() + CONTRAST_TRIM
    return prefijo + cuerpo


def validate_contrast(data, *, redactor, home_dir):
    """Devuelve `(contraste, problemas)`. Con problemas no se persiste nada.

    Los mismos gates que el resto: es texto de modelo y se guarda.
    """
    if not isinstance(data, dict):
        return None, ["el modelo no devolvió un objeto"]
    problemas = []
    salida = {}
    for campo in ("changed", "bought", "cost"):
        valor = data.get(campo)
        if isinstance(valor, str) and valor.strip():
            valor = " ".join(valor.split())
            problemas.extend(_leaks(valor, "contrast.%s" % campo, redactor, home_dir))
            salida[campo] = valor
    condiciones = []
    for item in (data.get("old_valid_when") or [])[:MAX_VALID_WHEN]:
        condicion = item.get("condition") if isinstance(item, dict) else item
        if isinstance(condicion, str) and condicion.strip():
            condicion = " ".join(condicion.split())
            problemas.extend(_leaks(condicion, "contrast.old_valid_when[]", redactor,
                                    home_dir))
            condiciones.append(condicion)
    if condiciones:
        salida["old_valid_when"] = condiciones
    if problemas:
        return None, problemas
    if not salida.get("changed"):
        return None, ["`changed` es obligatorio: sin él el contraste no dice nada"]
    return salida, []


def build_prompt(conn, group, *, ideate=True, modo=MODO_DE_IDEACION) -> str:
    """El prompt de consolidación. **Idear es el default y no hay config que lo apague.**

    `ideate=False` sobrevive por una sola razón: `experimentos/ideate.py` necesita el
    brazo de control para poder volver a medir la diferencia. Que el control sea
    alcanzable desde un experimento no lo vuelve una opción del producto.

    `modo` elige **con qué se idea**, nunca si se idea: `mermaid` (ADR-004, el default) o
    `fisica` (ADR-007, la escena antes del diagrama). Los dos empiezan pidiendo idear; lo
    que cambia es el medio, que es justo la variable que H17 dejó sin sostener.
    """
    if modo not in PREFIJOS_DE_IDEACION:
        raise DreamError("modo de ideación desconocido: %r (hay %s)"
                         % (modo, ", ".join(MODOS_DE_IDEACION)))
    partes = [describe(conn, row) for row in group[:MAX_TRAYECTORIAS_POR_GRUPO]]
    cuerpo = PROMPT % "\n".join(partes)
    return (PREFIJOS_DE_IDEACION[modo] + cuerpo) if ideate else cuerpo


# --------------------------------------------------------- el dibujo, como dibujo
#
# Hasta acá el diagrama se revisaba **sólo por fugas** y se inyectaba entero dentro de un
# bloque ` ```mermaid `, que promete renderizar. Un dibujo roto es peor que ninguno:
# ocupa el lugar del dibujo y no dice nada.
#
# Esto valida **sintaxis, no verdad**, y la distinción importa porque es fácil dejarla
# implícita: el diagrama de la candidata `1f94f424` es Mermaid perfectamente válido y
# describe un mecanismo que no existe. Para eso está la clasificación de pasos de más
# abajo, no esto.
CABECERAS_MERMAID = ("flowchart", "graph", "sequencediagram", "statediagram-v2",
                     "statediagram", "classdiagram", "erdiagram")
MAX_NODOS_DIAGRAMA = 10
# Las aristas de Mermaid en el subconjunto que el prompt pide. `-->`, `---`, `-.->`,
# `==>`, con o sin etiqueta, y las de `sequenceDiagram` (`->>`, `-->>`).
_ARISTA_RE = re.compile(r"(-{2,3}>>?|-\.->|={2,3}>|-{2,3}|->>)")
# Un identificador de nodo: lo que va antes del corchete, el paréntesis o la llave.
_NODO_RE = re.compile(r"([A-Za-z_][A-Za-z0-9_]*)\s*(?:[\[\(\{]|$|\s)")


def validate_diagram(diagram: str):
    """Motivos por los que este texto no es un diagrama utilizable. Vacío = está bien.

    Determinista y con stdlib: la validez de Mermaid es sintáctica y decidible, así que
    preguntársela a un modelo sería cambiar un gate por un juicio (CLAUDE.md, regla 2).
    """
    problemas = []
    lineas = [l.strip() for l in (diagram or "").splitlines() if l.strip()]
    if not lineas:
        return ["el diagrama está vacío"]

    cabecera = lineas[0].lower()
    if not any(cabecera.startswith(c) for c in CABECERAS_MERMAID):
        problemas.append("la primera línea no declara un tipo de diagrama conocido: %r"
                         % lineas[0][:40])

    cuerpo = "\n".join(lineas[1:])
    # Un backtick suelto cierra el bloque ` ```mermaid ` al inyectarlo y desde ahí el
    # resto de la memoria se lee como prosa. Es el único carácter que rompe el continente
    # y no el contenido.
    if "`" in diagram:
        problemas.append("el diagrama tiene un backtick: rompe el bloque al inyectarlo")
    for abre, cierra in (("[", "]"), ("(", ")"), ("{", "}")):
        if cuerpo.count(abre) != cuerpo.count(cierra):
            problemas.append("corchetes `%s%s` desbalanceados: %d contra %d"
                             % (abre, cierra, cuerpo.count(abre), cuerpo.count(cierra)))

    nodos = set()
    for linea in lineas[1:]:
        if linea.lower().startswith(("subgraph", "end", "style", "classdef", "click",
                                     "direction", "participant", "note", "%%")):
            continue
        for parte in _ARISTA_RE.split(linea):
            parte = parte.strip()
            if not parte or _ARISTA_RE.fullmatch(parte):
                continue
            # La etiqueta de una arista (`|así|`) no declara un nodo.
            parte = re.sub(r"\|[^|]*\|", " ", parte).strip()
            match = _NODO_RE.match(parte)
            if match:
                nodos.add(match.group(1))
    if len(nodos) > MAX_NODOS_DIAGRAMA:
        # El tope estaba sólo en el prompt, que es una pedido y no un gate. Un diagrama
        # que no entra de un vistazo no es un dibujo, es un plano.
        problemas.append("%d nodos: el tope es %d, y un diagrama que no entra de un"
                         " vistazo no es un dibujo" % (len(nodos), MAX_NODOS_DIAGRAMA))
    if not nodos:
        problemas.append("no se reconoce ningún nodo: no hay dibujo")
    return problemas


# ---------------------------------------------------------------- validación
def _leaks(text, field, redactor, home_dir):
    """Motivos por los que un texto producido por el modelo no puede persistirse."""
    problemas = []
    if audit.ABSTRACTION_PATH_RE.search(text):
        problemas.append("%s contiene una secuencia tipo path (el esquema la rechaza)" % field)
    if redactor.text(text) != text:
        problemas.append("%s contiene material que el redactor tiene que tapar "
                         "(identificador del repo, secreto, correo o ruta)" % field)
    for hallazgo in audit.scan_value(text, field, redactor=redactor, home_dir=home_dir):
        problemas.append("%s dispara la regla %s del auditor" % (field, hallazgo["rule"]))
    return problemas


# ------------------------------------------------ la escena, como escena (ADR-007)
#
# El gate que hace real la palabra «física». Sin esto, «traducí a una escena física» es un
# pedido, y un pedido no es un gate (CLAUDE.md regla 2): el modelo puede contestar con la
# explicación de siempre encabezada por «imaginá una máquina» y nada lo notaría.
#
# Lo que se revisa es **que la traducción haya ocurrido**, no que la escena sea verdadera.
# La distinción es la misma que ya vale para el diagrama: `validate_diagram` contesta «¿va
# a renderizar?» y nunca «¿es cierto?». Una escena preciosa de un mecanismo que no existe
# pasa este gate igual, y eso lo ataca el anclaje a observaciones, no esto.

# Vocabulario que delata que la escena no se fue del dominio del software. Es corto a
# propósito: cada palabra de más es un rechazo falso que le cuesta un reintento al modelo,
# así que están sólo las que no tienen ninguna lectura física razonable. `rama`, `bandera`,
# `línea` y `cliente` NO están, y no por olvido: en una escena son un árbol, un mástil, una
# línea de montaje y quien compra.
VOCABULARIO_DEL_CODIGO = (
    "archivo", "archivos", "carpeta", "carpetas", "directorio", "directorios",
    "funcion", "funciones", "variable", "variables", "clase", "clases",
    "metodo", "metodos", "parametro", "parametros", "codigo", "software",
    "programa", "compilador", "compilar", "script", "scripts", "test", "tests",
    "linter", "lint", "prompt", "hook", "hooks", "commit", "commits", "repo",
    "repositorio", "json", "sqlite", "sql", "cache", "string", "array", "hash",
    "api", "endpoint", "http", "url", "servidor", "log", "logs", "stdout",
    "stderr", "bug", "bugs", "excepcion", "timeout", "byte", "bytes", "buffer",
    "thread", "token", "tokens", "deploy", "build", "import", "config", "flag",
    "debug", "stack", "backend", "frontend", "runtime",
)

# Formas que sólo tiene un identificador: `algo_asi`, `algoAsi`, `algo()`, `algo.py`.
IDENTIFICADOR = re.compile(r"[a-z0-9]+_[a-z0-9_]+|[a-z]+[A-Z][a-zA-Z]*|\w+\(\)"
                           r"|\w+\.(py|json|md|sh|sql|js|ts|txt|yml|yaml)\b")

MIN_PALABRAS_ESCENA = 25
MAX_PALABRAS_ESCENA = 220
MIN_PALABRAS_LOGOGRAMA = 2
MAX_PALABRAS_LOGOGRAMA = 4
MAX_CARACTERES_LOGOGRAMA = 48


def _sin_acentos(texto: str) -> str:
    """Comparar con acentos deja pasar `función` cuando la lista dice `funcion`."""
    import unicodedata
    return "".join(c for c in unicodedata.normalize("NFD", texto)
                   if unicodedata.category(c) != "Mn")


def _palabras_del_codigo(texto: str):
    """Qué términos del dominio del software aparecen, como palabra entera."""
    plano = _sin_acentos((texto or "").lower())
    tokens = set(re.findall(r"[a-z0-9]+", plano))
    return sorted(t for t in VOCABULARIO_DEL_CODIGO if t in tokens)


def validate_scene(scene: str):
    """Motivos por los que este texto no es una escena física. Vacío = está bien."""
    problemas = []
    texto = (scene or "").strip()
    if not texto:
        return ["la escena está vacía"]
    palabras = texto.split()
    if len(palabras) < MIN_PALABRAS_ESCENA:
        # Una imagen que no se puede recorrer no muestra dónde se pierde algo: es un
        # rótulo, y el rótulo ya es el logograma.
        problemas.append("%d palabras: una escena que no se puede recorrer no muestra "
                         "dónde se pierde algo (mínimo %d)"
                         % (len(palabras), MIN_PALABRAS_ESCENA))
    if len(palabras) > MAX_PALABRAS_ESCENA:
        problemas.append("%d palabras: eso ya no es una imagen, es un informe (máximo %d)"
                         % (len(palabras), MAX_PALABRAS_ESCENA))
    delatores = _palabras_del_codigo(texto)
    if delatores:
        problemas.append("nombra el dominio del software (%s): la traducción a una escena "
                         "física no se hizo" % ", ".join(delatores[:5]))
    identificadores = sorted(set(m.group(0) for m in IDENTIFICADOR.finditer(texto)))
    if identificadores:
        problemas.append("tiene identificadores de código (%s): en una máquina no hay "
                         "nada que se llame así" % ", ".join(identificadores[:3]))
    if "`" in texto:
        problemas.append("tiene un backtick: la escena se inyecta como prosa")
    return problemas


def validate_logogram(logogram: str):
    """Motivos por los que esto no es un logograma. Vacío = está bien.

    Dos a cuatro palabras que **nombran** el mecanismo. Estirado a una oración deja de
    comprimir; encogido a una palabra no dice qué le pasa a qué.
    """
    problemas = []
    texto = " ".join((logogram or "").split())
    if not texto:
        return ["el logograma está vacío"]
    if len(texto) > MAX_CARACTERES_LOGOGRAMA:
        problemas.append("%d caracteres: un signo que no entra de un vistazo no es un "
                         "signo (máximo %d)" % (len(texto), MAX_CARACTERES_LOGOGRAMA))
    palabras = texto.split()
    if not MIN_PALABRAS_LOGOGRAMA <= len(palabras) <= MAX_PALABRAS_LOGOGRAMA:
        problemas.append("%d palabra(s): el logograma va de %d a %d — una sola no dice qué "
                         "le pasa a qué, y más de cuatro ya es una oración"
                         % (len(palabras), MIN_PALABRAS_LOGOGRAMA,
                            MAX_PALABRAS_LOGOGRAMA))
    delatores = _palabras_del_codigo(texto)
    if delatores:
        # Medido el 2026-08-28 para las señales: un nombre propio de herramienta engancha
        # con cualquier otro problema de esa herramienta.
        problemas.append("nombra el dominio del software (%s): un signo alrededor de una "
                         "herramienta vale para cualquier problema de esa herramienta"
                         % ", ".join(delatores[:3]))
    if re.search(r"[.;:`]", texto):
        problemas.append("tiene puntuación de oración: un logograma no se puntúa")
    return problemas


def validate(data, *, redactor, home_dir, ideation=None, observation_indices=None,
             modo=MODO_DE_IDEACION):
    """Devuelve `(abstraction, valid_when, hypothesis, problemas)`.

    Con problemas, no se persiste nada.

    `modo` es con qué se ideó (ADR-007). En `fisica` el dibujo es la escena y el diagrama
    se descarta aunque el modelo lo devuelva: si un brazo guardara los dos medios, la
    comparación pasaría a ser entre acumular texto y no acumularlo — que es exactamente lo
    que H17 midió y castigó.

    `ideation` es el boceto del que salió la abstracción, si se ideó. Pasa por los mismos
    gates de fuga que todo lo demás: es texto de modelo y se persiste igual. Y vuelve
    dentro de `abstraction["_ideation"]`, que `consolidate` saca antes de guardar —
    la clave con guión bajo no llega al JSON persistido.
    """
    problemas = []
    if not isinstance(data, dict):
        return None, None, None, ["el modelo no devolvió un objeto"]

    pattern = data.get("pattern")
    if pattern is None:
        return None, None, None, [SIN_PATRON]
    if not isinstance(pattern, str) or len(pattern.strip()) < 20:
        return None, None, None, ["`pattern` tiene que ser un texto de al menos 20 "
                                  "caracteres"]
    pattern = " ".join(pattern.split())
    problemas.extend(_leaks(pattern, "abstraction.pattern", redactor, home_dir))

    signals = []
    for item in (data.get("signals") or [])[:MAX_SIGNALS]:
        if isinstance(item, str) and item.strip():
            item = " ".join(item.split())
            problemas.extend(_leaks(item, "abstraction.signals[]", redactor, home_dir))
            signals.append(item)

    decisive = data.get("decisive_signal")
    if isinstance(decisive, str) and decisive.strip():
        decisive = " ".join(decisive.split())
        problemas.extend(_leaks(decisive, "abstraction.decisive_signal", redactor, home_dir))
    else:
        decisive = None

    valid_when = []
    for item in (data.get("valid_when") or [])[:MAX_VALID_WHEN]:
        condition = item.get("condition") if isinstance(item, dict) else item
        if isinstance(condition, str) and condition.strip():
            condition = " ".join(condition.split())
            problemas.extend(_leaks(condition, "valid_when[].condition", redactor, home_dir))
            valid_when.append({"condition": condition, "source": "inferred"})

    # La hipótesis es de la trayectoria, no de la abstracción, pero pasa por los mismos
    # gates: es texto del modelo y se persiste igual que el resto.
    hypothesis = data.get("hypothesis")
    if isinstance(hypothesis, str) and hypothesis.strip():
        hypothesis = " ".join(hypothesis.split())
        problemas.extend(_leaks(hypothesis, "hypothesis", redactor, home_dir))
        # **El primer eslabón se ancla o no existe** (plan §7, F2). `observation_indices`
        # son los pasos que NO son lectura del repo: los que observan algo de esta sesión.
        #
        # Esto no vuelve verdadera una hipótesis —el modelo puede citar un paso que no
        # dice lo que él cree— pero le pone un costo a inventar y la hace auditable con
        # `why`. Y sobre todo cierra el caso medido: la hipótesis falsa del 2026-08-28
        # salía de dos `grep`, y contra lecturas ya no se puede anclar.
        if observation_indices is not None:
            paso = data.get("hypothesis_step")
            if not isinstance(paso, int) or paso not in observation_indices:
                # No es un rechazo de la consolidación entera: la hipótesis es un campo
                # opcional y `null` es una respuesta válida. Volteart todo el grupo por
                # esto perdería el patrón, que es lo que sí vale.
                hypothesis = None
    else:
        hypothesis = None

    # Proyectado: lo que este mecanismo produciría y nadie vio. Se valida igual que
    # `signals` y se guarda aparte, nunca mezclado. Un síntoma anticipado que se cuela
    # entre los observados deja de ser una conjetura y pasa a ser un dato falso.
    proyectados = []
    for item in (data.get("projected_signals") or [])[:MAX_SIGNALS]:
        if isinstance(item, str) and item.strip():
            item = " ".join(item.split())
            problemas.extend(_leaks(item, "projected_signals[]", redactor, home_dir))
            if item not in signals:      # proyectar algo ya observado no proyecta nada
                proyectados.append(item)

    # El dibujo llega en dos campos: el diagrama Mermaid y la prosa del mecanismo. Los
    # dos son texto de modelo y se persisten, así que pasan los mismos gates — y el
    # diagrama **más** que el resto: las etiquetas de un flowchart son justo donde alguien
    # escribiría una ruta de archivo sin pensarlo.
    diagram = data.get("diagram") if modo == "mermaid" else None
    if isinstance(diagram, str) and diagram.strip():
        # Al diagrama no se le colapsan los saltos de línea: en Mermaid son sintaxis.
        diagram = diagram.strip()
        problemas.extend(_leaks(diagram, "diagram", redactor, home_dir))
        # Y como diagrama, no sólo como texto. Un rechazo acá entra al mismo bucle de
        # reintentos que una fuga: el modelo recibe el motivo y vuelve a intentar.
        problemas.extend("diagram: %s" % p for p in validate_diagram(diagram))
    else:
        diagram = None

    mecanismo = data.get("mechanism")
    if isinstance(mecanismo, str) and mecanismo.strip():
        mecanismo = " ".join(mecanismo.split())
        problemas.extend(_leaks(mecanismo, "mechanism", redactor, home_dir))
    else:
        mecanismo = None

    # La escena y el logograma: el otro medio de idear. Pasan los mismos gates que todo
    # lo demás —son texto de modelo y se persisten— y además los suyos: una escena que
    # nombra el dominio del software no tradujo nada, y un logograma que es una oración no
    # comprime nada. Los dos rechazos entran al mismo bucle de reintentos que una fuga.
    escena = data.get("physical_scene") if modo == "fisica" else None
    if isinstance(escena, str) and escena.strip():
        escena = " ".join(escena.split())
        problemas.extend(_leaks(escena, "physical_scene", redactor, home_dir))
        problemas.extend("physical_scene: %s" % p for p in validate_scene(escena))
    else:
        escena = None

    logograma = data.get("logogram") if modo == "fisica" else None
    if isinstance(logograma, str) and logograma.strip():
        logograma = " ".join(logograma.split())
        problemas.extend(_leaks(logograma, "logogram", redactor, home_dir))
        problemas.extend("logogram: %s" % p for p in validate_logogram(logograma))
    else:
        logograma = None

    # `ideation` es la prosa del mecanismo. El campo `mechanism` del JSON gana sobre las
    # marcas `<ideacion>`, que quedan por las respuestas del formato anterior.
    ideation = mecanismo or ideation
    if isinstance(ideation, str) and ideation.strip():
        ideation = " ".join(ideation.split())
        if ideation is not mecanismo:
            problemas.extend(_leaks(ideation, "ideation", redactor, home_dir))
    else:
        ideation = None

    if problemas:
        return None, None, None, problemas

    abstraction = {"pattern": pattern}
    if proyectados:
        abstraction["_projected_signals"] = proyectados
    if ideation:
        abstraction["_ideation"] = ideation
    if diagram:
        abstraction["_diagram"] = diagram
    if escena:
        abstraction["_physical_scene"] = escena
    if logograma:
        abstraction["_logogram"] = logograma
    if signals:
        abstraction["signals"] = signals
    if decisive:
        abstraction["decisive_signal"] = decisive
    return abstraction, valid_when, hypothesis, []


# ------------------------------------------------------------------ consolidar
def consolidate(conn, model, *, cfg=None, identifiers=None, lookback_days=None,
                max_groups=None, dry_run=False, log=None, only_trajectory=None,
                modo=MODO_DE_IDEACION) -> dict:
    """Ejecuta la fase 1 completa. Devuelve un reporte; no imprime nada.

    `modo` elige el medio de la ideación (ADR-007): `mermaid`, el default, o `fisica`, la
    escena antes del diagrama. **No hay valor que apague la ideación**, y el reporte dice
    cuál corrió — una corrida con un medio no es comparable con otra, exactamente por el
    mismo motivo por el que `consolidation_strategy` dejó de ser una clave de config.

    `max_groups` limita cuántos grupos consolida esta corrida. Cada grupo llama al
    modelo, y desde ADR-003 eso cuesta (el backend `claude-code` cobra por token). El
    límite corta por los primeros grupos en el orden estable de `groups()`; los que
    quedan afuera no se pierden, se consolidan en la próxima corrida.

    `only_trajectory` acota la corrida a los grupos que **contienen** esa trayectoria. Es
    lo que necesita un ciclo de sueño a demanda: sellar un capítulo y consolidar la semana
    entera cuesta la semana entera, y quien pidió dormir sobre lo que acaba de hacer no
    pidió eso. Filtra por pertenencia y no por posición, que es lo que `max_groups` no
    puede hacer.
    """
    cfg = cfg or config.load()
    lookback = lookback_days if lookback_days is not None else cfg.get("dream_lookback_days", 7)
    max_groups = max_groups if max_groups is not None else cfg.get("dream_max_groups")
    redactor = Redactor(identifiers=identifiers or [], deny_paths=cfg.get("deny_paths", []),
                        home_dir=cfg.get("_home_dir"))
    home_dir = cfg.get("_home_dir")
    say = log or (lambda _message: None)
    # **Idear es el flujo, no una estrategia entre dos** (ADR-004, enmienda 0.3.7).
    #
    # Hasta acá `consolidation_strategy` elegía entre `observed` —abstraer lo que las
    # trayectorias muestran— e `ideate` —dibujar el mecanismo, abstraer desde el dibujo y
    # proyectar los síntomas que nadie vio. El interruptor ya no existe: `consolidate`
    # idea siempre, y no hay clave de config que lo apague.
    #
    # El motivo es que las dos ramas no consolidan lo mismo con más o menos detalle:
    # `observed` no puede producir `projected_signals`, y sin proyecciones el retrieval
    # sólo puede engancharse con un síntoma **después** de que se vio una vez. Dejar eso
    # detrás de una clave de config era dejar la capacidad entera detrás de un default.
    #
    # El brazo de control no se pierde: `build_prompt(..., ideate=False)` sigue existiendo
    # para `experimentos/ideate.py`, que es donde se mide la diferencia. Lo que se perdió
    # es la posibilidad de que una corrida del plugin no idee sin que nadie lo note.
    idear = True
    if modo not in MODOS_DE_IDEACION:
        raise DreamError("modo de ideación desconocido: %r (hay %s)"
                         % (modo, ", ".join(MODOS_DE_IDEACION)))

    todos = groups(conn, lookback_days=lookback)
    if only_trajectory:
        todos = [g for g in todos if any(r["id"] == only_trajectory for r in g)]
    limitados = todos[:max_groups] if max_groups is not None else todos
    saltados_por_limite = len(todos) - len(limitados)

    reporte = {"model": model.name, "lookback_days": lookback, "groups": 0,
               "groups_total": len(todos), "groups_skipped_by_limit": saltados_por_limite,
               "only_trajectory": only_trajectory,
               "cost_usd": None, "input_tokens": 0, "output_tokens": 0,
               # Siempre explícito desde la 0.3.10: "ideate:<modo>". Un registro que dice
               # sólo "ideate" deja de decir CON QUÉ se ideó el día que el default cambia
               # — y acaba de cambiar.
               "strategy": "ideate:%s" % modo,
               "trajectories": 0, "candidates": [], "superseded": [], "rejected": [],
               "skipped": [], "dry_run": bool(dry_run)}

    if saltados_por_limite:
        say("%d grupo(s) sin consolidar por --max-groups=%d: quedan para la próxima corrida"
            % (saltados_por_limite, max_groups))

    for group in limitados:
        reporte["groups"] += 1
        reporte["trajectories"] += len(group)

        # Las siluetas no van al modelo. Preguntarle por seis líneas vacías cuesta —
        # medido, 38.127 tokens de entrada por un grupo— y la respuesta que devuelve es
        # "no hay patrón", que después se lee como si el material se hubiera mirado.
        utiles = [row for row in group if tiene_contenido(conn, row)]
        if not utiles:
            say("grupo de %d · sin contenido capturado: no se le pregunta al modelo"
                % len(group))
            reporte["skipped"].append({"trajectory": group[-1]["id"],
                                       "reason": SIN_CONTENIDO})
            continue

        # El representante se elige entre las que tienen contenido: promover una silueta
        # con la abstracción que salió de otra trayectoria sería atribuirla mal.
        winner = representative(utiles)
        vacias = len(group) - len(utiles)
        say("grupo de %d%s · representante %s (%s)"
            % (len(group), " (%d sin contenido, no se muestran)" % vacias if vacias else "",
               winner["id"][:8], winner["task_type"]))

        prompt = build_prompt(conn, utiles, ideate=idear, modo=modo)
        abstraction = valid_when = hypothesis = None
        problemas = []
        costo_antes = getattr(model, "total_cost", 0.0) or 0.0
        for intento in range(1 + REINTENTOS):
            try:
                data = model.ask_json(prompt if intento == 0
                                      else prompt + RETRY_SUFFIX % "\n".join(
                                          "- %s" % p for p in problemas))
            except ModelUnavailable:
                # Sin modelo no hay dream: eso aborta todo, no un grupo.
                raise
            except DreamError as exc:
                # Un grupo que el modelo arruinó no puede llevarse puesta la corrida
                # entera: se anota y se sigue con el siguiente.
                abstraction, valid_when, hypothesis = None, None, None
                problemas = [str(exc)]
                say("  intento %d falló: %s" % (intento + 1, exc))
                continue
            abstraction, valid_when, hypothesis, problemas = validate(
                data, redactor=redactor, home_dir=home_dir,
                ideation=getattr(model, "last_ideation", None),
                observation_indices=indices_de_observacion(conn, utiles), modo=modo)
            if not problemas:
                break
            if problemas == [SIN_PATRON]:
                # El modelo dijo que estas trayectorias no comparten nada. Insistir es
                # pedirle que invente: se salta el grupo.
                break
            say("  intento %d rechazado: %s" % (intento + 1, "; ".join(problemas)))

        if problemas == [SIN_PATRON]:
            say("  sin patrón común: el grupo se salta")
            reporte["skipped"].append({"trajectory": winner["id"], "reason": SIN_PATRON})
            continue
        if problemas:
            reporte["rejected"].append({"trajectory": winner["id"], "reasons": problemas})
            continue

        # Costo atribuible a este grupo: lo gastado entre el arranque del intento y acá,
        # incluidos los reintentos. `or None` porque un backend que no reporta costo
        # (el modelo local) y uno que reportó exactamente 0 son indistinguibles con un
        # float, y "no reportado" es la lectura correcta por defecto (spec §1.3 cond. 3).
        costo_grupo = (getattr(model, "total_cost", 0.0) or 0.0) - costo_antes

        # Se leen antes de que `promote_to_candidate` las saque del dict.
        ideacion_del_grupo = abstraction.get("_ideation")
        diagrama_del_grupo = abstraction.get("_diagram")
        escena_del_grupo = abstraction.get("_physical_scene")
        logograma_del_grupo = abstraction.get("_logogram")
        proyectados_del_grupo = list(abstraction.get("_projected_signals") or [])

        if not dry_run:
            # Las claves con guión bajo son de transporte: `validate` las usa para
            # devolver ideación y proyecciones sin estirar la tupla, y acá se sacan
            # antes de persistir. Lo que se guarda en `abstraction_json` es lo que
            # define `trajectory.v1` y nada más.
            ideacion = abstraction.pop("_ideation", None)
            proyectados = abstraction.pop("_projected_signals", None)
            diagrama = abstraction.pop("_diagram", None)
            escena = abstraction.pop("_physical_scene", None)
            logograma = abstraction.pop("_logogram", None)
            estado = store.promote_to_candidate(conn, winner["id"], abstraction=abstraction,
                                                valid_when=valid_when,
                                                hypothesis=hypothesis,
                                                weight=CANDIDATE_WEIGHT,
                                                consolidation_model=model.name,
                                                consolidation_cost_usd=costo_grupo or None,
                                                ideation=ideacion,
                                                projected_signals=proyectados,
                                                diagram=diagrama,
                                                physical_scene=escena,
                                                logogram=logograma)
            if estado != "candidate":
                # La promoción exige `closed`. Si la trayectoria cambió de estado entre
                # que se agrupó y que se promovió, el UPDATE no toca nada — y un reporte
                # que igual la lista como candidata es un reporte que miente.
                say("  %s no se promovió: quedó en %s" % (winner["id"][:8], estado))
                reporte["rejected"].append({
                    "trajectory": winner["id"],
                    "reasons": ["la promoción no se aplicó: la trayectoria está en `%s`,"
                                " no en `closed`" % estado]})
                continue
        reporte["candidates"].append({"trajectory": winner["id"],
                                      "task_type": winner["task_type"],
                                      "pattern": abstraction["pattern"],
                                      "hypothesis": hypothesis,
                                      "valid_when": len(valid_when),
                                      "ideation": ideacion_del_grupo,
                                      "diagram": diagrama_del_grupo,
                                      "physical_scene": escena_del_grupo,
                                      "logogram": logograma_del_grupo,
                                      "projected_signals": len(proyectados_del_grupo)})

        for old in contradicted_by(conn, group, winner):
            # La diferencia entre las dos es la lección, y hasta acá no la calculaba
            # nadie: el enlace decía *que* una reemplazó a la otra, nunca qué cambió ni
            # cuándo la vieja seguía teniendo razón. Es una llamada más al modelo, y sólo
            # ocurre cuando hay una contradicción registrada — que es raro.
            contraste = None
            try:
                datos = model.ask_json(build_contrast_prompt(conn, old, winner,
                                                             ideate=idear, modo=modo))
                contraste, malos = validate_contrast(datos, redactor=redactor,
                                                     home_dir=home_dir)
                if malos:
                    say("  contraste de %s rechazado: %s" % (old["id"][:8],
                                                             "; ".join(malos)))
            except ModelUnavailable:
                raise
            except DreamError as exc:
                # Un contraste que falla no puede llevarse puesta la supersesión: el
                # enlace vale por sí solo, y perderlo sería borrar lo contradicho —
                # exactamente lo que ADR-001 dice que no hacemos.
                say("  contraste de %s falló: %s" % (old["id"][:8], exc))
            if not dry_run:
                store.mark_superseded(conn, old["id"], winner["id"], contrast=contraste)
            reporte["superseded"].append({"trajectory": old["id"], "by": winner["id"],
                                          "contrast": contraste})
            say("  %s contradicha por %s: superseded, no borrada%s"
                % (old["id"][:8], winner["id"][:8],
                   " (con contraste)" if contraste else ""))

    reporte["cost_usd"] = getattr(model, "total_cost", None) or None
    reporte["input_tokens"] = getattr(model, "total_input_tokens", 0) or 0
    reporte["output_tokens"] = getattr(model, "total_output_tokens", 0) or 0
    return reporte


def redactor_identifiers(cwd="."):
    """Identificadores del repo desde donde se corre dream.

    El store no guarda nombres de repo — sólo el fingerprint — así que esto es lo único
    que dream sabe del repo actual. Es una red parcial y honesta: cubre el repo desde el
    que se corre, no todos los que produjeron trayectorias.
    """
    try:
        return context.repo_identifiers(cwd)
    except Exception:
        return []
