from .texto import normalizar


def totales(filas):
    salida = {}
    for fila in filas:
        clave = normalizar(fila["clave"])
        salida[clave] = salida.get(clave, 0) + fila["valor"]
    return salida
