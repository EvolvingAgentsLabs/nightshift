from .texto import normalizar

PERMITIDAS = {"alta", "baja", "modificacion"}


def es_valida(fila):
    return normalizar(fila["accion"]) in PERMITIDAS
