from .ajustes import LIMITES


def consultar(cliente):
    return cliente.pedir(tiempo_limite=LIMITES["consulta_ms"])


def escribir(cliente):
    return cliente.enviar(tiempo_limite=LIMITES["escritura_ms"])


def lote(cliente):
    return cliente.despachar(tiempo_limite=LIMITES["lote_ms"])
