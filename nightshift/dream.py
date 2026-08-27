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
        lines.append("  - %s%s (`%s`): %s"
                     % (step["kind"], " DECISIVO" if step["decisive"] else "",
                        step["tool"] or "—", detail))
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

PROMPT = """Sos el consolidador de nightshift. Te doy trayectorias de trabajo ya
capturadas y redactadas: pasos de herramientas, fallos y señales. Tu única tarea es
abstraer el patrón que comparten.

Devolvé SÓLO un objeto JSON, sin texto alrededor, con esta forma exacta:

{
  "pattern": "forma del problema y del fix, en 1-3 oraciones",
  "hypothesis": "la hipótesis con la que arrancó el trabajo, en una oración",
  "signals": ["señal observable que indica que este patrón aplica"],
  "decisive_signal": "la observación que volvió concluyente el diagnóstico",
  "valid_when": ["precondición bajo la que este procedimiento aplica"],
  "projected_signals": ["síntoma que este mecanismo produciría y que NADIE observó"],
  "diagram": "diagrama Mermaid del mecanismo, sólo si te pidieron idear",
  "mechanism": "qué se conserva y qué se pierde, sólo si te pidieron idear"
}

Reglas duras. Una respuesta que las rompa se descarta:

- `pattern` describe la ESTRUCTURA, no el caso. Nada de rutas de archivo, nombres de
  repositorio, de paquete, de archivo, de rama, ni dominios. Ni `/algo/`, ni `~/`, ni
  `../`. Si necesitás nombrar un archivo, decí "el módulo afectado".
- Todo en español, sin markdown, sin backticks dentro de los strings.
- `signals` y `valid_when`: como mucho 5 elementos cada uno, oraciones cortas.
- `hypothesis` es **el primer eslabón de la cadena causal**: con qué se creyó que era el
  problema al empezar, aunque después resultara equivocada. Si de los pasos no se puede
  inferir ninguna, poné null en vez de escribir una obvia.
- `signals` es lo que SE VIO en estas trayectorias. `projected_signals` es lo que el
  mismo mecanismo produciría en otra parte y no se vio. Nunca pongas en `signals` algo
  que no esté en los pasos: la diferencia entre observar y anticipar es la única que
  hace que esto sea memoria y no adivinación. Si no te pidieron idear, dejá
  `projected_signals` vacío.
- Si las trayectorias no comparten ningún patrón útil, devolvé
  {"pattern": null} en lugar de inventar uno.

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


def build_contrast_prompt(conn, old_row, new_row, *, ideate=True) -> str:
    """El contraste también se idea. `ideate=False` existe sólo para el brazo de control
    de `experimentos/ideate.py`: en el plugin no hay ninguna ruta que lo apague."""
    cuerpo = CONTRAST_PROMPT % (describe(conn, old_row), describe(conn, new_row))
    return (IDEATE_PREFIX + cuerpo) if ideate else cuerpo


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


def build_prompt(conn, group, *, ideate=True) -> str:
    """El prompt de consolidación. **Idear es el default y no hay config que lo apague.**

    `ideate=False` sobrevive por una sola razón: `experimentos/ideate.py` necesita el
    brazo de control para poder volver a medir la diferencia. Que el control sea
    alcanzable desde un experimento no lo vuelve una opción del producto.
    """
    partes = [describe(conn, row) for row in group[:MAX_TRAYECTORIAS_POR_GRUPO]]
    cuerpo = PROMPT % "\n".join(partes)
    return (IDEATE_PREFIX + cuerpo) if ideate else cuerpo


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


def validate(data, *, redactor, home_dir, ideation=None):
    """Devuelve `(abstraction, valid_when, hypothesis, problemas)`.

    Con problemas, no se persiste nada.

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
    diagram = data.get("diagram")
    if isinstance(diagram, str) and diagram.strip():
        # Al diagrama no se le colapsan los saltos de línea: en Mermaid son sintaxis.
        diagram = diagram.strip()
        problemas.extend(_leaks(diagram, "diagram", redactor, home_dir))
    else:
        diagram = None

    mecanismo = data.get("mechanism")
    if isinstance(mecanismo, str) and mecanismo.strip():
        mecanismo = " ".join(mecanismo.split())
        problemas.extend(_leaks(mecanismo, "mechanism", redactor, home_dir))
    else:
        mecanismo = None

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
    if signals:
        abstraction["signals"] = signals
    if decisive:
        abstraction["decisive_signal"] = decisive
    return abstraction, valid_when, hypothesis, []


# ------------------------------------------------------------------ consolidar
def consolidate(conn, model, *, cfg=None, identifiers=None, lookback_days=None,
                max_groups=None, dry_run=False, log=None) -> dict:
    """Ejecuta la fase 1 completa. Devuelve un reporte; no imprime nada.

    `max_groups` limita cuántos grupos consolida esta corrida. Cada grupo llama al
    modelo, y desde ADR-003 eso cuesta (el backend `claude-code` cobra por token). El
    límite corta por los primeros grupos en el orden estable de `groups()`; los que
    quedan afuera no se pierden, se consolidan en la próxima corrida.
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

    todos = groups(conn, lookback_days=lookback)
    limitados = todos[:max_groups] if max_groups is not None else todos
    saltados_por_limite = len(todos) - len(limitados)

    reporte = {"model": model.name, "lookback_days": lookback, "groups": 0,
               "groups_total": len(todos), "groups_skipped_by_limit": saltados_por_limite,
               "cost_usd": None, "input_tokens": 0, "output_tokens": 0,
               "strategy": "ideate",
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

        prompt = build_prompt(conn, utiles, ideate=idear)
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
                ideation=getattr(model, "last_ideation", None))
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
        proyectados_del_grupo = list(abstraction.get("_projected_signals") or [])

        if not dry_run:
            # Las claves con guión bajo son de transporte: `validate` las usa para
            # devolver ideación y proyecciones sin estirar la tupla, y acá se sacan
            # antes de persistir. Lo que se guarda en `abstraction_json` es lo que
            # define `trajectory.v1` y nada más.
            ideacion = abstraction.pop("_ideation", None)
            proyectados = abstraction.pop("_projected_signals", None)
            diagrama = abstraction.pop("_diagram", None)
            estado = store.promote_to_candidate(conn, winner["id"], abstraction=abstraction,
                                                valid_when=valid_when,
                                                hypothesis=hypothesis,
                                                weight=CANDIDATE_WEIGHT,
                                                consolidation_model=model.name,
                                                consolidation_cost_usd=costo_grupo or None,
                                                ideation=ideacion,
                                                projected_signals=proyectados,
                                                diagram=diagrama)
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
                                      "projected_signals": len(proyectados_del_grupo)})

        for old in contradicted_by(conn, group, winner):
            # La diferencia entre las dos es la lección, y hasta acá no la calculaba
            # nadie: el enlace decía *que* una reemplazó a la otra, nunca qué cambió ni
            # cuándo la vieja seguía teniendo razón. Es una llamada más al modelo, y sólo
            # ocurre cuando hay una contradicción registrada — que es raro.
            contraste = None
            try:
                datos = model.ask_json(build_contrast_prompt(conn, old, winner,
                                                             ideate=idear))
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
