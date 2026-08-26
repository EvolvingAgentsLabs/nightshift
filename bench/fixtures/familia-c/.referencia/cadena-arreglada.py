from . import etapas

CADENA = [etapas.escalar, etapas.redondear, etapas.rotular]


def procesar(lecturas):
    """Pasa cada lectura por la cadena entera.

    Si una etapa falla, el error sube diciendo cuál fue. Taparlo mueve el síntoma a la
    etapa siguiente, donde ya no se puede diagnosticar.
    """
    salida = []
    for lectura in lecturas:
        actual = lectura
        for etapa in CADENA:
            try:
                actual = etapa(actual)
            except Exception as error:
                raise RuntimeError("la etapa %s falló: %s" % (etapa.__name__, error))
        salida.append(actual)
    return salida


def promedio(lecturas):
    procesadas = procesar(lecturas)
    if not procesadas:
        return 0
    return sum(l["magnitud"] for l in procesadas) / len(procesadas)
