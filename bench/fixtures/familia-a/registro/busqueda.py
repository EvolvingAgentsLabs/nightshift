from .texto import normalizar


def contiene(filas, termino):
    aguja = normalizar(termino)
    return [f for f in filas if aguja in normalizar(f["clave"])]
