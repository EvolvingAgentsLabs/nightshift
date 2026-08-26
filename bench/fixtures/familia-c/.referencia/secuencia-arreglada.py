from . import pasos

SECUENCIA = [pasos.acortar, pasos.decada, pasos.encabezar]


def ejecutar(fichas):
    """Hace atravesar la secuencia completa a cada ficha.

    Si un paso falla, el error sube diciendo cuál fue.
    """
    resultado = []
    for ficha in fichas:
        vigente = ficha
        for paso in SECUENCIA:
            try:
                vigente = paso(vigente)
            except Exception as error:
                raise RuntimeError("el paso %s falló: %s" % (paso.__name__, error))
        resultado.append(vigente)
    return resultado


def indice(fichas):
    return {f["titulo"]: f["anio"] for f in ejecutar(fichas) if f["titulo"]}
