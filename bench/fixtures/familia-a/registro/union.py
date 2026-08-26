from .texto import normalizar


def unir(izquierda, derecha):
    por_clave = {normalizar(fila["clave"]): fila for fila in derecha}
    salida = []
    for fila in izquierda:
        pareja = por_clave.get(normalizar(fila["clave"]))
        if pareja is not None:
            salida.append((fila, pareja))
    return salida
