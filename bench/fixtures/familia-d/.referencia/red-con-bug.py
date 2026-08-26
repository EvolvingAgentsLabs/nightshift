from .ajustes import LIMITES


def consultar(cliente):
    # El límite está escrito acá y no sale de LIMITES: cambiar los ajustes no hace nada.
    return cliente.pedir(tiempo_limite=1000)


def escribir(cliente):
    return cliente.enviar(tiempo_limite=1000)


def lote(cliente):
    return cliente.despachar(tiempo_limite=5000)
