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

**Y le falta un eslabón, anotado el 2026-08-28 a la noche.** Este módulo llama a
`candidates` + `render` directo, y el camino de verdad tiene una compuerta más arriba:
`hook.on_user_prompt_submit` sólo rankea en el prompt que fija el tipo de tarea, y sale
temprano cuando el tipo sigue siendo `general`. Los tres síntomas retenidos clasifican como
`general`, así que **ninguno habría producido una inyección en una sesión real**. Lo que
mide este módulo es el ranking; lo que llega al agente puede ser menos. Es el mismo error de
altitud que corrigió el `08`, una capa más arriba, y está en `LATER.md` con las tres
opciones de spec que abre. Hasta que se cierre, todo número que salga de acá se lee como
**cota superior**.

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


def montar(d, abstraccion, proyecciones=None):
    """Mete la abstracción de un brazo por el camino real: candidata con proyecciones."""
    tid = d.store.open_trajectory(d.conn, session_id="s", repo_fingerprint=REPO,
                                  task_type=TASK, base_commit="abc1234",
                                  redaction={"redactor_version": "0.1.0"})
    d.store.append_step(d.conn, tid, kind="tool_failure", tool="run_shell",
                        error_message="AssertionError en el borde", decisive=True)
    d.store.close_trajectory(d.conn, tid, result="tests_passed")
    d.store.promote_to_candidate(
        d.conn, tid,
        abstraction={k: abstraccion[k] for k in ("pattern", "signals", "decisive_signal")
                     if abstraccion.get(k)},
        valid_when=condiciones(abstraccion.get("valid_when")),
        hypothesis=None, weight=0.6,
        projected_signals=list(proyecciones or []) or None,
        diagram=abstraccion.get("diagram"))
    return tid


def llega(d, cfg, prompt):
    """¿La memoria llega al bloque que ve el agente, y llega **por enganche**?

    Devuelve `(inyectada, engancha, motivos)`. `inyectada` sola no alcanza: en un store con
    una fila, `same_repo` la inyecta siempre. Lo que se mide es `engancha`, que es lo que
    distingue "habla de tu problema" de "es del mismo repo".
    """
    from nightshift import retrieve
    scored = retrieve.candidates(d.conn, task_type=TASK, repo_fingerprint=REPO,
                                 cfg=cfg, prompt=prompt)
    texto, elegidas = retrieve.render(d.conn, scored,
                                      max_injected=cfg.get("max_injected", 3),
                                      native_memory=None, task_type=TASK,
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
        marcador = {"retenidos": 0, "ajenos": 0}
        detalle = []
        for etiqueta, prompt in retenidos:
            inyectada, engancha, motivos = llega(d, cfg, prompt)
            marcador["retenidos"] += bool(engancha)
            detalle.append({"etiqueta": etiqueta, "prompt": prompt, "clase": "retenido",
                            "engancha": bool(engancha), "inyectada": inyectada,
                            "motivos": motivos})
        for prompt in ajenos:
            inyectada, engancha, motivos = llega(d, cfg, prompt)
            marcador["ajenos"] += bool(engancha)
            detalle.append({"etiqueta": "AJENO", "prompt": prompt, "clase": "ajeno",
                            "engancha": bool(engancha), "inyectada": inyectada,
                            "motivos": motivos})
    marcador["detalle"] = detalle
    return marcador
