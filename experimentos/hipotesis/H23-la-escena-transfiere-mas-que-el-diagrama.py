"""H23 — ¿La escena física transfiere donde el diagrama no?"""
import importlib.util
import json
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _marco import PASS, FAIL, BLOCKED, StoreDesechable, correr_solo

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(
    os.path.abspath(__file__)))))
import camino_real                                                  # noqa: E402

IDEA = 'idear'
HIPOTESIS = 'La escena fisica transfiere a un sintoma que no se vio, y el diagrama no.'

# El corpus: los dos brazos consolidando la MISMA trayectoria del retenido.
TRAYECTORIA = "5b3ff97f"

# Control negativo, el mismo de H17.
AJENOS = ["el certificado ssl del dominio vencio y el deploy no arranca",
          "quiero agregar paginacion a la tabla de usuarios",
          "el linter se queja de un import sin usar"]


def _leer_retenido(ruta):
    """El parser del `12`, importado y no copiado: dos copias de un parser se separan."""
    raiz = ruta.parent.parent
    spec = importlib.util.spec_from_file_location(
        "sensibilidad", raiz / "12-sensibilidad.py")
    modulo = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(modulo)
    return modulo.leer_retenido(ruta)


def correr():
    """Medido por el camino real, con una advertencia que vale más que el número.

    **El retenido de `5b3ff97f` lo escribió el agente** (autorización de Matías,
    2026-08-28, y el archivo lo dice arriba de todo): el mismo autor del retrieval, de
    los prompts de los dos brazos y de este instrumento. Así que lo que esto mide es un
    **techo de autor** — si ni así un brazo transfiere, no transfiere; si transfiere,
    todavía no se sabe si le transfiere a una persona. La versión humana del retenido
    sigue pendiente (`retenido/PENDIENTE-5b3ff97f.md`) y es la única que puede convertir
    este veredicto en uno de transferencia real.

    Las dos salidas salen de `14 --trajectory 5b3ff97f`: los dos brazos consolidando la
    misma trayectoria, con el bucle de reintentos del plugin.
    """
    from pathlib import Path
    raiz = Path(__file__).resolve().parent.parent.parent
    salidas = raiz / "experimentos" / "salidas"
    retenido = raiz / "experimentos" / "retenido" / ("%s.md" % TRAYECTORIA)

    faltan = []
    brazos = {}
    for modo in ("mermaid", "fisica"):
        ruta = salidas / ("14-%s-%s.json" % (modo, TRAYECTORIA))
        if ruta.is_file():
            brazos[modo] = json.loads(ruta.read_text(encoding="utf-8"))
        else:
            faltan.append("la salida del brazo %s: `python3 experimentos/"
                          "14-la-escena-antes-del-diagrama.py --trajectory %s`"
                          % (modo, TRAYECTORIA))
    if not retenido.is_file():
        faltan.append("el retenido `%s`" % retenido.name)
    if faltan:
        return BLOCKED, ("no se puede comprobar todavia:\n"
                         + "\n".join("  - %s" % f for f in faltan))

    filas = [f for f in _leer_retenido(retenido) if f["frase"]]
    if not filas:
        return BLOCKED, "el retenido existe pero no tiene frases"
    retenidos = [("conjetura %d" % i, f["frase"]) for i, f in enumerate(filas, 1)]

    marcadores = {}
    for modo, data in brazos.items():
        proyecciones = [p for p in (data.get("projected_signals") or [])
                        if isinstance(p, str)]
        marcadores[modo] = camino_real.medir(data, proyecciones, retenidos, AJENOS)

    c, i = marcadores["mermaid"], marcadores["fisica"]
    numeros = ("  retenidos (%d): mermaid %d, fisica %d.\n"
               "  control negativo (%d): mermaid %d, fisica %d."
               % (len(retenidos), c["retenidos"], i["retenidos"],
                  len(AJENOS), c["ajenos"], i["ajenos"]))

    # La procedencia decide qué clase de veredicto puede salir de acá. Contra un retenido
    # escrito por el agente —el mismo autor del retrieval, de los prompts de los dos
    # brazos y de este instrumento— NO hay veredicto de transferencia posible: ni un PASS
    # (se estaria midiendo a si mismo) ni un FAIL (sus frases evitan sustantivos con un
    # criterio que una persona real no aplica). El numero se registra y la hipotesis
    # ESPERA el material que si puede decidirla. Eso es BLOCKED, no FAIL: confundirlos
    # convierte una espera en un fracaso, y este repo ya pago esa confusion.
    de_autor = "agente" in retenido.read_text(encoding="utf-8")[:1200].lower()
    if de_autor:
        return BLOCKED, ("el unico retenido disponible lo escribio el agente (techo de\n"
                         "autor): con el se registra el numero y no un veredicto.\n"
                         + numeros + "\n"
                         "La version humana sigue pendiente en\n"
                         "`retenido/PENDIENTE-5b3ff97f.md`, y es la unica que puede\n"
                         "decidir esta hipotesis.")

    if i["retenidos"] > c["retenidos"] and i["ajenos"] == 0:
        return PASS, ("la escena engancha mas que el diagrama sin comprar ajenos.\n"
                      + numeros)
    if i["retenidos"] == 0 and c["retenidos"] == 0:
        return FAIL, ("NINGUNO de los dos brazos engancha ni un retenido: antes de\n"
                      "comparar medios hay que llegar, y ninguno llega.\n" + numeros)
    return FAIL, ("el resultado NO favorece a la escena:\n" + numeros)


if __name__ == "__main__":
    sys.exit(correr_solo(sys.modules[__name__]))
