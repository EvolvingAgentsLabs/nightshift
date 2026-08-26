from .texto import normalizar


def construir(filas):
    return {normalizar(fila["clave"]): fila for fila in filas}


def buscar(indice, clave):
    return indice[normalizar(clave)]
