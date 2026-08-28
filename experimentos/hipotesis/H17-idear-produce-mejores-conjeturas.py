"""H17 — ¿Idear produce transferencia que no idear no compra?"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _marco import PASS, FAIL, BLOCKED, StoreDesechable, correr_solo

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(
    os.path.abspath(__file__)))))
import camino_real                                                  # noqa: E402

IDEA = "idear"
HIPOTESIS = "Idear compra transferencia a un sintoma que no se vio, y no idear no."

# Los tres sintomas que una persona confirmo despues (`nightshift resolve`), dichos con
# palabras humanas. Ninguno de los dos brazos los vio.
RETENIDOS = [
    ("panel de salud con denominador cero",
     "el resumen dice que esta todo bien pero no conto ninguna celda"),
    ("ensayo verde contra store vacio",
     "la corrida termina en verde y no proceso ni un solo caso"),
    ("linter con lista vacia",
     "el chequeo pasa porque su patron no encontro ningun archivo"),
]

# Control negativo. Sin esto, un brazo que engancha con todo pareceria el mejor.
AJENOS = ["el certificado ssl del dominio vencio y el deploy no arranca",
          "quiero agregar paginacion a la tabla de usuarios",
          "el linter se queja de un import sin usar"]


def correr():
    """Se mide contra un conjunto RETENIDO y por el CAMINO REAL.

    Dos decisiones, y las dos costaron un error antes:

    - El conjunto retenido son sintomas de `cbbd7ff0` que una persona confirmo despues,
      con parafrasis escritas a mano. Ninguno de los dos brazos los vio.
    - La medicion la hace `camino_real.medir`: monta la abstraccion como candidata y
      rankea con `retrieve.candidates`. Hasta el 2026-08-28 esto armaba un bolson de
      frases con `signals + pattern + decisive_signal`, y la cadena real nunca matchea
      contra `pattern`: el control anotaba un enganche que la maquina no produce.

    El veredicto pide las dos mitades. Enganchar mas retenidos comprando un prompt ajeno
    no es transferencia: es superficie. Un brazo con mas texto engancha mas de las dos
    cosas, y sin el control negativo eso se lee como una victoria.

    La salida del brazo de control esta guardada en `experimentos/salidas/` para que esto
    corra sin llamar al modelo. Regenerarla: `python3 experimentos/07-idear-contra-no-idear.py`.
    """
    import json
    from pathlib import Path
    from nightshift import store

    raiz = Path(__file__).resolve().parent.parent.parent
    guardado = raiz / "experimentos" / "salidas" / "07-control-observed.json"
    if not guardado.is_file():
        return BLOCKED, ("falta la salida del brazo de control. Regenerarla cuesta una\n"
                         "llamada al modelo: python3 experimentos/07-idear-contra-no-idear.py")

    conn = store.connect()
    try:
        fila = conn.execute("SELECT * FROM trajectories WHERE id LIKE 'cbbd7ff0%'").fetchone()
        if fila is None or not fila["abstraction_json"]:
            return BLOCKED, ("la candidata `cbbd7ff0` no esta en este store. El experimento\n"
                             "mide contra sintomas que una persona confirmo, y sin ese\n"
                             "material no hay conjunto retenido.")
        ideado = json.loads(fila["abstraction_json"])
        proyectadas = [p["text"] for p in store.projections_of(conn, fila["id"])]
    finally:
        conn.close()
    control = json.loads(guardado.read_text(encoding="utf-8"))

    c = camino_real.medir(control, [], RETENIDOS, AJENOS)
    i = camino_real.medir(ideado, proyectadas, RETENIDOS, AJENOS)

    if i["retenidos"] > c["retenidos"] and i["ajenos"] == 0:
        return PASS, ("idear engancha %d de %d retenidos contra %d del control, y no\n"
                      "engancha ningun prompt ajeno." % (i["retenidos"], len(RETENIDOS),
                                                         c["retenidos"]))
    if i["retenidos"] <= c["retenidos"]:
        return FAIL, ("MEDIDO por el camino real, y el resultado NO favorece a idear:\n"
                      "  retenidos: control %d, ideado %d de %d.\n"
                      "Sobre n=1 corpus, idear no compro transferencia."
                      % (c["retenidos"], i["retenidos"], len(RETENIDOS)))
    ajenos = [d["prompt"] for d in i["detalle"] if d["clase"] == "ajeno" and d["engancha"]]
    return FAIL, ("MEDIDO por el camino real. Idear engancha mas, y lo paga:\n"
                  "  retenidos: control %d, ideado %d de %d.\n"
                  "  control negativo: control %d, ideado %d de %d.\n"
                  "  el brazo ideado engancho: %s\n"
                  "Mas superficie engancha mas de las dos cosas. Mientras el control\n"
                  "negativo no de 0, la transferencia extra no se puede separar de la\n"
                  "indiscriminacion, y esta hipotesis pide justamente esa separacion.\n"
                  "NO refuta ADR-004: la deja sin sostener, que es distinto.\n"
                  "Para cerrarla hace falta volumen, y es lo mismo que le falta a todo lo\n"
                  "demas de este repo."
                  % (c["retenidos"], i["retenidos"], len(RETENIDOS),
                     c["ajenos"], i["ajenos"], len(AJENOS),
                     "; ".join(ajenos) or "(ninguno)"))


if __name__ == "__main__":
    sys.exit(correr_solo(sys.modules[__name__]))
