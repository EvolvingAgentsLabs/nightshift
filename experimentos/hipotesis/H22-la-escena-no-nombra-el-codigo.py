"""H22 — ¿La escena física es física, o es la misma prosa con otro título?"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _marco import PASS, FAIL, BLOCKED, StoreDesechable, correr_solo

IDEA = 'idear'
HIPOTESIS = 'Una escena que nombra el codigo no llega a candidate: el gate la rechaza.'

# Una escena que sí se fue al plano físico. Ninguna palabra del dominio del software.
ESCENA = ("Una cinta transportadora lleva cajas selladas hasta una balanza que decide si "
          "cada una sigue viaje. La balanza pesa la caja entera, sin abrirla, y una caja "
          "vacia pesa casi lo mismo que una llena de aire. Cuando el llenado falla, el "
          "sello se coloca igual y la balanza la aprueba: nadie mira adentro hasta el "
          "final de la linea, donde ya no se sabe en que tramo se vacio.")

# La misma explicación de siempre encabezada por «imaginá una máquina». Es exactamente lo
# que este gate existe para atrapar: si pasa, «traducí a una escena física» es un deseo.
DISFRAZADA = ("Imagina una maquina donde la funcion de validacion recibe un archivo y "
              "revisa solamente su forma, nunca su contenido, asi que el test pasa igual "
              "y el error aparece mucho despues, lejos de donde se origino todo esto.")


def correr():
    """Se ejercita el camino real: `dream.validate` con el modo `fisica`, que es el que
    corre `consolidate`. Un gate que sólo existe como función suelta no es un gate.

    Las dos mitades importan y son distintas:

    - la escena buena **pasa** — un gate que rechaza todo no discrimina, cuesta reintentos
      y termina apagándose;
    - la escena disfrazada **se rechaza por el motivo correcto**, nombrando qué palabra la
      delató. Un rechazo sin motivo no entra al bucle de reintentos como algo que el modelo
      pueda corregir.
    """
    from nightshift import config, dream, redact

    redactor = redact.Redactor(identifiers=[], deny_paths=config.DEFAULT_DENY_PATHS,
                               home_dir=None)
    base = {"pattern": "Una etapa sella el resultado sin mirar lo que quedo adentro."}

    buena, _, _, problemas = dream.validate(
        dict(base, physical_scene=ESCENA, logogram="caja sellada vacia"),
        redactor=redactor, home_dir=None, modo="fisica")
    if problemas:
        return FAIL, ("una escena fisica legitima fue rechazada: %s\n"
                      "Un gate que rechaza todo no discrimina: cuesta reintentos y termina\n"
                      "apagandose." % "; ".join(problemas))
    if buena.get("_physical_scene") != ESCENA or not buena.get("_logogram"):
        return FAIL, "la escena paso pero no llego a la abstraccion"

    _, _, _, problemas = dream.validate(
        dict(base, physical_scene=DISFRAZADA, logogram="validacion ciega"),
        redactor=redactor, home_dir=None, modo="fisica")
    escena = [p for p in problemas if p.startswith("physical_scene:")]
    if not escena:
        return FAIL, ("la misma prosa de siempre con el titulo «imagina una maquina» paso\n"
                      "el gate. Entonces «traducilo a una escena fisica» es un pedido, y un\n"
                      "pedido no es un gate (CLAUDE.md regla 2).")

    # Y el logograma: dos a cuatro palabras que no nombren una herramienta.
    if dream.validate_logogram("centinela ciego"):
        return FAIL, "un logograma legitimo de dos palabras fue rechazado"
    for malo, por_que in (("caja", "una sola palabra no dice que le pasa a que"),
                          ("una caja que se sella vacia y pesa igual que una llena",
                           "una oracion no comprime nada"),
                          ("linter vacio", "nombra una herramienta")):
        if not dream.validate_logogram(malo):
            return FAIL, "paso un logograma que no lo es (%s): %s" % (malo, por_que)

    return PASS, ("la escena disfrazada se rechaza nombrando la palabra que la delata:\n"
                  "  %s\n"
                  "y la escena fisica legitima pasa. El logograma exige de dos a cuatro\n"
                  "palabras y ninguna herramienta.\n"
                  "Esto valida la TRADUCCION, nunca la verdad: una escena preciosa de un\n"
                  "mecanismo que no existe pasa este gate igual, como pasa un Mermaid\n"
                  "perfectamente valido (`1f94f424`). Eso lo ataca el anclaje a\n"
                  "observaciones, no esto." % escena[0])


if __name__ == "__main__":
    sys.exit(correr_solo(sys.modules[__name__]))
