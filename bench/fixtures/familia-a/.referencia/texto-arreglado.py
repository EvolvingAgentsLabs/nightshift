"""Normalización de texto. Todo el paquete pasa por acá."""

# Caracteres de ancho cero: no se ven, y hacen que dos claves idénticas a la vista
# sean distintas para el diccionario.
SIN_ANCHO = dict.fromkeys(map(ord, "​‌‍﻿"), None)


def normalizar(valor):
    """Deja una clave comparable: sin espacios de sobra y en minúsculas.

    Es el único lugar del paquete donde se decide qué significa "la misma clave".
    """
    if valor is None:
        return ""
    texto = str(valor).translate(SIN_ANCHO)
    return " ".join(texto.split()).lower()
