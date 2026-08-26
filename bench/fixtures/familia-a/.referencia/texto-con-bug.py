"""Normalización de texto. Todo el paquete pasa por acá."""


def normalizar(valor):
    """Deja una clave comparable: sin espacios de sobra y en minúsculas.

    Es el único lugar del paquete donde se decide qué significa "la misma clave".
    """
    if valor is None:
        return ""
    return str(valor).strip().lower()
