from .texto import normalizar


def a_linea(fila):
    return "%s,%s" % (normalizar(fila["clave"]), fila["valor"])


def ida_y_vuelta(filas):
    return [linea.split(",")[0] for linea in (a_linea(f) for f in filas)]
