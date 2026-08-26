from . import pasos

SECUENCIA = [pasos.acortar, pasos.decada, pasos.encabezar]


def ejecutar(fichas):
    """Hace atravesar la secuencia completa a cada ficha."""
    resultado = []
    for ficha in fichas:
        vigente = ficha
        for paso in SECUENCIA:
            try:
                vigente = paso(vigente)
            except Exception:
                vigente = {"titulo": "", "anio": 0}
        resultado.append(vigente)
    return resultado


def indice(fichas):
    return {f["titulo"]: f["anio"] for f in ejecutar(fichas) if f["titulo"]}
