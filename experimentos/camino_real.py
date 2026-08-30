"""El instrumento es la máquina, no una reimplementación parecida.

Este módulo existe por un error concreto, y el error vale más que el módulo.

`07-idear-contra-no-idear.py` y `H17` medían el enganche con un bolsón de frases armado a
mano: `signals + pattern + decisive_signal`. La cadena real —`retrieve.candidates`— hace
otra cosa:

- **nunca** matchea contra `pattern`, y
- sí matchea contra `valid_when`, que el bolsón no miraba.

Resultado: el brazo de control anotaba un enganche que en la cadena real no ocurre, y el
`FAIL` de H17 se apoyaba en parte en un número que la máquina no produce. El diagnóstico
está en `08-el-techo-del-oraculo.py`; la corrección es esto: **medir por el camino real**.
No hay bolsón de frases en ningún lado. Se monta la abstracción como candidata con
`promote_to_candidate`, se rankea con `retrieve.candidates` y se arma el bloque con
`retrieve.render`, que es literalmente lo que hace el hook. Si la cadena cambia, la
medición cambia con ella y no hay una segunda definición que se quede vieja.

Corolario que conviene tener escrito: **que un helper devuelva un número no es que el
agente lo vea.** Lo que cuenta es que la fila llegue al `additionalContext`.

**El eslabón que le faltaba, y ahora está: la compuerta del clasificador.** Hasta el
2026-08-28 a la noche este módulo llamaba a `candidates` + `render` directo, y el camino de
verdad tiene una compuerta más arriba: `hook.on_user_prompt_submit` sólo rankea en el
prompt que **fija** el tipo de tarea, y sale temprano cuando `classify_task` devuelve
`general`. Los tres síntomas retenidos clasifican como `general`, así que ninguno habría
producido una inyección en una sesión real por más alto que rankeara.

Por eso `medir` devuelve **dos marcadores y no uno**, y no son intercambiables:

- **`retenidos` / `ajenos` — lo que RANKEA.** Es el número de siempre, el que publicaron el
  `07`, el `09` y H17. No cambió, y no se toca: reescribirlo haría irreproducible todo lo
  que ya está escrito.
- **`retenidos_llegan` / `ajenos_llegan` — lo que LLEGA al agente.** Cuenta sólo los prompts
  que además pasan la compuerta. Es el número que corresponde citar cuando la pregunta es si
  la memoria sirve, y hoy es más chico.

Cuál se usa depende de la pregunta, y hay que decir cuál. "¿El ranking pone esta fila
arriba?" es lo primero; "¿el agente la ve?" es lo segundo, y una respuesta al primero
presentada como respuesta al segundo es el error de altitud que este repo ya cometió dos
veces en un día.

**Lo que este módulo sigue sin modelar, escrito para que no sorprenda:** la regla de una
inyección por trayectoria. `on_user_prompt_submit` inyecta en el prompt que fija el tipo y
nunca más; acá cada prompt se mide contra un store desechable propio, así que cada uno
tiene su oportunidad. Para medir una sesión entera haría falta otra cosa.

Todo corre sobre un `HOME` temporal. Nunca toca el store real.
"""

import os
import sys
import tempfile
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
if str(RAIZ) not in sys.path:
    sys.path.insert(0, str(RAIZ))

# Un repo y un tipo de tarea cualesquiera: lo que se compara entre brazos es el enganche
# con el prompt, y `same_repo`/`same_task_type` valen igual para todos.
REPO = "f" * 64
TASK = "implement_feature"


class StoreDesechable:
    """Un store nuevo en un HOME temporal. Nunca toca el store real."""

    def __enter__(self):
        self._home = os.environ.get("HOME")
        self._dir = tempfile.TemporaryDirectory(prefix="nightshift-camino-")
        os.environ["HOME"] = self._dir.name
        for modulo in ("nightshift.config", "nightshift.store"):
            sys.modules.pop(modulo, None)
        from nightshift import store
        self.store = store
        self.conn = store.connect()
        return self

    def __exit__(self, *exc):
        try:
            self.conn.close()
        finally:
            if self._home is not None:
                os.environ["HOME"] = self._home
            self._dir.cleanup()
        return False


def condiciones(items):
    """La forma que guarda el store es la que arma `dream.validate`, no la del modelo.

    El modelo devuelve strings; `validate` las envuelve en `{"condition", "source"}` antes
    de que lleguen a la base. Un experimento que compara salidas ya escritas hace la misma
    conversión, o estaría montando un brazo con una forma que el camino real nunca produce
    — y `valid_when` es justamente uno de los campos contra los que se engancha.
    """
    salida = []
    for item in items or ():
        if isinstance(item, dict) and item.get("condition"):
            salida.append(item)
        elif isinstance(item, str) and item.strip():
            salida.append({"condition": item, "source": "inferred"})
    return salida


def montar(d, abstraccion, proyecciones=None, *, physical_scene=None, logogram=None):
    """Mete la abstracción de un brazo por el camino real: candidata con proyecciones.

    `physical_scene` y `logogram` (ADR-007) viajan a sus columnas. No cambian el ranking
    —se muestran y no se buscan— pero un caso montado sin ellos no es el caso entero, y
    `render` tiene que poder mostrarlos.
    """
    tid = d.store.open_trajectory(d.conn, session_id="s", repo_fingerprint=REPO,
                                  task_type=TASK, base_commit="abc1234",
                                  redaction={"redactor_version": "0.1.0"})
    d.store.append_step(d.conn, tid, kind="tool_failure", tool="run_shell",
                        error_message="AssertionError en el borde", decisive=True)
    d.store.close_trajectory(d.conn, tid, result="tests_passed")
    d.store.promote_to_candidate(
        d.conn, tid,
        # La lista blanca es la del esquema, y **crece cuando el esquema crece**. Se
        # dejó afuera `colloquial_queries` (enmienda 0.3.13) y la medición del brazo
        # nuevo salió en verde midiendo el brazo viejo: exit 0, números plausibles, campo
        # ausente. Es el `plano viejo, pieza real` de la candidata `16a5f7ff`, cometido
        # el mismo día que esa memoria se inyectó en la sesión que lo cometió.
        abstraction={k: abstraccion[k] for k in ("pattern", "signals", "decisive_signal",
                                                 "colloquial_queries")
                     if abstraccion.get(k)},
        valid_when=condiciones(abstraccion.get("valid_when")),
        hypothesis=None, weight=0.6,
        projected_signals=list(proyecciones or []) or None,
        diagram=abstraccion.get("diagram"),
        physical_scene=physical_scene, logogram=logogram)
    return tid


def compuerta(prompt):
    """¿`on_user_prompt_submit` llegaría siquiera a rankear con este prompt?

    Devuelve `(pasa, tipo)`. **Desde la enmienda 0.3.10, `pasa` es siempre `True`**: la
    compuerta del clasificador dejó de existir para la inyección — todos los prompts se
    evalúan, y lo que discrimina es el enganche con su piso en 2. Lo medido que motivó la
    decisión: los tres retenidos de H17 y los seis casos diseñados del `15` clasificaban
    `general`, así que el techo entero llegaba al agente 0 de N veces.

    La función se conserva —y sigue llamando a `classify_task`, no reimplementándolo—
    porque `tipo` sigue importando: es el que el hook le pasa a `candidates`, y de ahí
    sale `same_task_type`. Los números "llega" publicados ANTES de la 0.3.10 se midieron
    con la compuerta vieja y no son comparables con los de después.
    """
    from nightshift import context
    tipo = context.classify_task(prompt)
    return True, tipo


def llega(d, cfg, prompt, tipo=None):
    """¿La memoria llega al bloque que ve el agente, y llega **por enganche**?

    Devuelve `(inyectada, engancha, motivos)`. `inyectada` sola no alcanza: en un store con
    una fila, `same_repo` la inyecta siempre. Lo que se mide es `engancha`, que es lo que
    distingue "habla de tu problema" de "es del mismo repo".

    `tipo` es el que **clasificó el prompt**, no el de la candidata: es lo que le pasa el
    hook a `candidates`, y de ahí sale `same_task_type`. Pasarle el tipo de la candidata
    regalaría un bonus que en una sesión real depende de lo que el usuario escribió.
    """
    from nightshift import retrieve
    tipo = tipo or TASK
    scored = retrieve.candidates(d.conn, task_type=tipo, repo_fingerprint=REPO,
                                 cfg=cfg, prompt=prompt)
    texto, elegidas = retrieve.render(d.conn, scored,
                                      max_injected=cfg.get("max_injected", 3),
                                      native_memory=None, task_type=tipo,
                                      repo_fingerprint=REPO)
    motivos = scored[0][1] if scored else ""
    engancha = bool(retrieve.MOTIVOS_DE_ENGANCHE & set(motivos.split(",")))
    return bool(texto and elegidas), engancha, motivos


def medir(abstraccion, proyecciones, retenidos, ajenos):
    """Un brazo, de punta a punta, sobre un store desechable propio.

    `retenidos` es una lista de `(etiqueta, prompt)`; `ajenos`, de prompts. Devuelve el
    marcador y el detalle por prompt, para que un enganche se pueda auditar de a uno.
    """
    from nightshift import config
    with StoreDesechable() as d:
        montar(d, abstraccion, proyecciones)
        cfg = config.load()
        marcador = {"retenidos": 0, "ajenos": 0,
                    "retenidos_llegan": 0, "ajenos_llegan": 0}
        detalle = []
        for clase, items in (("retenido", retenidos),
                             ("ajeno", [("AJENO", p) for p in ajenos])):
            for etiqueta, prompt in items:
                pasa, tipo = compuerta(prompt)
                inyectada, engancha, motivos = llega(d, cfg, prompt, tipo=tipo)
                # La compuerta va primero: si el hook sale temprano, lo que el ranking
                # hubiera puesto arriba no existe para el agente.
                llegada = pasa and engancha
                marcador[clase + "s"] += bool(engancha)
                marcador[clase + "s_llegan"] += bool(llegada)
                detalle.append({"etiqueta": etiqueta, "prompt": prompt, "clase": clase,
                                "engancha": bool(engancha), "inyectada": inyectada,
                                "motivos": motivos, "clasifica": tipo,
                                "compuerta": pasa, "llega": llegada})
    marcador["detalle"] = detalle
    return marcador
