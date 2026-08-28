"""Cache del catálogo por producto."""

from . import ajustes


class Cache:
    def __init__(self):
        self.datos = {}
        self.aciertos = 0
        self.fallos = 0

    def get(self, clave):
        if clave in self.datos:
            self.aciertos += 1
            return self.datos[clave]
        self.fallos += 1
        return None

    def set(self, clave, valor, ttl=ajustes.CACHE_TTL_SEGUNDOS):
        if ttl <= 0:
            return valor
        self.datos[clave] = valor
        return valor


_CACHE = Cache()


def reiniciar():
    """Para los tests: el cache es global, como en el servicio de verdad."""
    global _CACHE
    _CACHE = Cache()
    return _CACHE


def _clave(producto, moneda):
    """La clave del cache."""
    return "producto:%s" % producto["id"]


def precio(producto, moneda, buscar):
    """Devuelve el precio del producto en esa moneda, cacheado."""
    clave = _clave(producto, moneda)
    valor = _CACHE.get(clave)
    if valor is None:
        valor = buscar(producto, moneda)
        _CACHE.set(clave, valor)
    return valor
