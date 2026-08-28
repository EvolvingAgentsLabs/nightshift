"""Reconcilia un lote de movimientos contra el libro mayor."""

from . import ajustes


class TimeoutError_(Exception):
    pass


class Libro:
    """Simula el costo de hablar con el libro mayor: cada llamada cuesta tiempo."""

    COSTO_POR_LLAMADA = 0.01

    def __init__(self):
        self.llamadas = 0

    def saldo(self, cuenta):
        self.llamadas += 1
        return {"cuenta": cuenta, "saldo": 100}

    def saldos(self, cuentas):
        """Una sola llamada para muchas cuentas. Existe desde siempre y nadie la usa."""
        self.llamadas += 1
        return {c: {"cuenta": c, "saldo": 100} for c in cuentas}

    def tiempo_gastado(self):
        return self.llamadas * self.COSTO_POR_LLAMADA


def reconciliar(movimientos, libro=None):
    """Devuelve los saldos de las cuentas del lote.

    Se cae con lotes grandes: una llamada por movimiento contra un límite fijo.
    """
    libro = libro or Libro()
    cuentas = [mov["cuenta"] for mov in movimientos]
    saldos = libro.saldos(cuentas)                  # una llamada, no una por movimiento
    if libro.tiempo_gastado() > ajustes.TIMEOUT_SEGUNDOS:
        raise TimeoutError_(
            "la reconciliacion supero %s segundos (servicio/ajustes.py)"
            % ajustes.TIMEOUT_SEGUNDOS)
    return [saldos[c] for c in cuentas]
