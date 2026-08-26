def acortar(ficha):
    return {"titulo": ficha["titulo"][:40], "anio": ficha["anio"]}


def decada(ficha):
    return {"titulo": ficha["titulo"], "anio": ficha["anio"] - (ficha["anio"] % 10)}


def encabezar(ficha):
    return {"titulo": ficha["titulo"].title(), "anio": ficha["anio"]}
