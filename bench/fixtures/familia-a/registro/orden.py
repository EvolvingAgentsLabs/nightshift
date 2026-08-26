from .texto import normalizar


def ordenar(filas):
    return sorted(filas, key=lambda fila: normalizar(fila["clave"]))
