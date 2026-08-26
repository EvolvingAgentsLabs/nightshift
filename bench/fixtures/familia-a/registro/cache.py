from .texto import normalizar


class Cache:
    def __init__(self):
        self._datos = {}
        self.aciertos = 0
        self.fallos = 0

    def obtener(self, clave, calcular):
        k = normalizar(clave)
        if k in self._datos:
            self.aciertos += 1
            return self._datos[k]
        self.fallos += 1
        self._datos[k] = calcular(clave)
        return self._datos[k]
