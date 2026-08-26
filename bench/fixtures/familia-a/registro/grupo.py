from .texto import normalizar


def agrupar(filas):
    salida = {}
    for fila in filas:
        salida.setdefault(normalizar(fila["clave"]), []).append(fila)
    return salida
