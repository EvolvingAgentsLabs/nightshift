from .texto import normalizar


def unicos(filas):
    vistos, salida = set(), []
    for fila in filas:
        clave = normalizar(fila["clave"])
        if clave in vistos:
            continue
        vistos.add(clave)
        salida.append(fila)
    return salida
