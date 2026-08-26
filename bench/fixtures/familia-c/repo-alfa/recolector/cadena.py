from . import etapas

CADENA = [etapas.escalar, etapas.redondear, etapas.rotular]


def procesar(lecturas):
    """Pasa cada lectura por la cadena entera."""
    salida = []
    for lectura in lecturas:
        actual = lectura
        for etapa in CADENA:
            try:
                actual = etapa(actual)
            except Exception:
                actual = {"sensor": "", "magnitud": 0}
        salida.append(actual)
    return salida


def promedio(lecturas):
    procesadas = procesar(lecturas)
    if not procesadas:
        return 0
    return sum(l["magnitud"] for l in procesadas) / len(procesadas)
