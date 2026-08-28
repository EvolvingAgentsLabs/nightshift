"""H17 — ¿Idear produce transferencia que no idear no compra?"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _marco import PASS, FAIL, BLOCKED, StoreDesechable, correr_solo

IDEA = "idear"
HIPOTESIS = "Idear compra transferencia a un sintoma que no se vio, y no idear no."


def correr():
    """Se mide contra un conjunto RETENIDO: sintomas de `cbbd7ff0` que una persona
    confirmo despues, con parafrasis escritas a mano. Ninguno de los dos brazos los vio.

    La salida del brazo de control esta guardada en `experimentos/salidas/` para que esto
    corra sin llamar al modelo. Regenerarla: `python3 experimentos/07-idear-contra-no-idear.py`.
    """
    import json
    from pathlib import Path
    from nightshift import retrieve, store

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

    def frases(a):
        out = list(a.get("signals") or [])
        for campo in ("pattern", "decisive_signal"):
            if a.get(campo):
                out.append(a[campo])
        return out

    RETENIDOS = ["el resumen dice que esta todo bien pero no conto ninguna celda",
                 "la corrida termina en verde y no proceso ni un solo caso",
                 "el chequeo pasa porque su patron no encontro ningun archivo"]

    def engancha(prompt, fs):
        return bool(retrieve._enganche(retrieve._tokens(prompt), fs,
                                       retrieve.MIN_TOKENS_DESTILADO))

    c = sum(engancha(p, frases(control)) for p in RETENIDOS)
    i = sum(engancha(p, frases(ideado) + proyectadas) for p in RETENIDOS)
    if i > c:
        return PASS, "idear engancha %d de %d contra %d del control" % (i, len(RETENIDOS), c)
    return FAIL, ("MEDIDO, y el resultado NO favorece a idear:\n"
                  "  transferencia a %d sintomas retenidos: control %d, ideado %d.\n"
                  "  control negativo: el brazo ideado engancho 1 prompt ajeno ('el linter\n"
                  "  se queja de un import sin usar' contra la proyeccion sobre un linter\n"
                  "  cuya lista quedo vacia) por compartir la palabra `linter`. Mismo\n"
                  "  sustantivo, problema distinto: es una colision mas debil que un falso\n"
                  "  positivo limpio, y el control no la hizo.\n"
                  "Sobre n=1 corpus, idear no compro transferencia y su superficie extra\n"
                  "costo una colision. NO cierra la apuesta de ADR-004: la deja sin\n"
                  "sostener, que es distinto de refutarla.\n"
                  "Para cerrarla hace falta volumen, y es lo mismo que le falta a todo lo\n"
                  "demas de este repo." % (len(RETENIDOS), c, i))


if __name__ == "__main__":
    sys.exit(correr_solo(sys.modules[__name__]))
