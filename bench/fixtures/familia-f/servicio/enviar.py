"""Envía un aviso al proveedor, con reintentos."""

from . import ajustes


class Proveedor:
    """El caso incómodo: el aviso **entra** y la respuesta se pierde en el camino.

    Desde afuera es indistinguible de un envío que no llegó, y por eso el reintento lo
    manda de nuevo.
    """

    def __init__(self, respuestas_perdidas=1):
        self._perdidas = respuestas_perdidas
        self.recibidos = []

    def enviar(self, aviso):
        # El proveedor sabe deduplicar: si el aviso trae `clave_idempotencia` y ya vio esa
        # clave, no lo vuelve a registrar. Está documentado desde siempre y nadie lo usa.
        clave = aviso.get("clave_idempotencia")
        if clave is None or clave not in {a.get("clave_idempotencia")
                                          for a in self.recibidos}:
            self.recibidos.append(aviso)
        if self._perdidas > 0:
            self._perdidas -= 1
            raise ConnectionError("se corto la conexion esperando la respuesta")
        return {"ok": True}


def enviar_aviso(aviso, proveedor=None):
    """Reintenta hasta `MAX_REINTENTOS`. No lleva clave de idempotencia."""
    proveedor = proveedor or Proveedor()
    ultimo = None
    for _ in range(ajustes.MAX_REINTENTOS):
        try:
            return proveedor.enviar(dict(aviso))
        except ConnectionError as exc:
            ultimo = exc
    raise ultimo
