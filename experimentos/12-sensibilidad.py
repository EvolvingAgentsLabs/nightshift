"""¿Llega la conjetura el día que hace falta? (sensibilidad contra un retenido nuevo)

**El número que falta.** `09-lectura-en-frio.py` midió que las conjeturas de este store son
específicas —enganchan 5 veces más con el síntoma que anticiparon que con cualquier otra
cosa— y que su **sensibilidad es 27%**: ninguna engancha más de 1 de los 3 síntomas
retenidos, y la primera que una persona confirmó no engancha ninguno. El problema del
proyecto no es que sobren conjeturas que se encienden con todo: es que faltan conjeturas
que se enciendan con lo suyo.

Se le agregaron a `dream.PROMPT` dos reglas que apuntan exactamente ahí —que `signals`,
`valid_when` y `projected_signals` son la única superficie contra la que se busca, y que se
escriben con los sustantivos del síntoma y no los del diseño— y **no se pueden medir contra
el retenido de `cbbd7ff0`**: ese conjunto se gastó diagnosticando, y el prompt se escribió
mirándolo. Medirlo ahí sería entrenar contra el test.

**Por eso este experimento no mide hasta que haya material.** Lee un archivo de
`experimentos/retenido/` escrito **por una persona que sólo vio las conjeturas**, y recién
entonces mide, por el camino real, cuántas engancha.

Mientras el archivo esté sin llenar, sale diciendo qué falta. Eso es `BLOCKED`, no `FAIL`:
la hipótesis no se puede comprobar todavía porque depende de material que no existe, y
confundir las dos cosas convierte una espera en un fracaso.

    python3 experimentos/12-sensibilidad.py
"""

import re
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ))
sys.path.insert(0, str(RAIZ / "experimentos"))

import camino_real                                                  # noqa: E402

RETENIDOS = RAIZ / "experimentos" / "retenido"

# Prompts ajenos: sin control negativo, un enganche alto no dice nada — puede ser
# sensibilidad o puede ser que engancha con todo. Son los mismos del `09`.
AJENOS = [
    "el bundle de webpack pesa 4 megas y la landing tarda en pintar",
    "el modelo entrena pero la loss se queda planchada desde la epoca 3",
    "la app de android crashea al rotar la pantalla en el detalle de producto",
    "el certificado ssl del dominio vencio y el deploy no arranca",
    "quiero agregar paginacion a la tabla de usuarios",
    "el test falla intermitentemente en ci pero pasa en local",
    "el mock del cliente http no se resetea entre tests",
    "el pipeline de ci falla en el paso de build por falta de memoria",
]

NEUTRA = {"pattern": "El mecanismo de la trayectoria que produjo esta conjetura."}


def leer_retenido(ruta):
    """Las conjeturas y la frase humana de cada una, del archivo del protocolo.

    El formato es el del archivo que llena la persona: `### n`, la conjetura citada con
    `>`, y después `tu frase:` con lo que escribió. Una sección sin frase no cuenta como
    fallo: cuenta como no respondida, y se informa aparte.
    """
    texto = ruta.read_text(encoding="utf-8")
    # El pie del archivo va después del último `---`, y si no se corta ahí, la instrucción
    # final se lee como si fuera la frase de la última conjetura.
    secciones = [s.split("\n---", 1)[0]
                 for s in re.split(r"^### \d+\s*$", texto, flags=re.MULTILINE)[1:]]
    salida = []
    for seccion in secciones:
        cita = " ".join(l.lstrip("> ").strip() for l in seccion.splitlines()
                        if l.startswith(">"))
        cuerpo = seccion.split("tu frase:", 1)
        frase = ""
        if len(cuerpo) == 2:
            for linea in cuerpo[1].splitlines():
                if linea.strip() and not linea.startswith("---"):
                    frase = linea.strip()
                    break
        if cita:
            salida.append({"conjetura": cita, "frase": frase})
    return salida


def main():
    archivos = sorted(RETENIDOS.glob("*.md"))
    pendientes = [a for a in archivos if a.name.startswith("PENDIENTE-")]
    listos = [a for a in archivos
              if not a.name.startswith("PENDIENTE-") and a.name != "README.md"]

    if not listos:
        print("BLOCKED — todavía no hay un conjunto retenido escrito por una persona.")
        print()
        for a in pendientes:
            filas = leer_retenido(a)
            sin = sum(1 for f in filas if not f["frase"])
            print("  %s: %d conjetura(s), %d sin frase" % (a.name, len(filas), sin))
        print()
        print("El protocolo está en `experimentos/retenido/README.md`. Lo que falta no es")
        print("código: es que alguien que sólo vio las conjeturas escriba con sus palabras")
        print("cómo describiría cada síntoma. No lo puede escribir quien mide — si las")
        print("paráfrasis las escribe el mismo que escribió el prompt, lo único que se")
        print("mide es cuánto se parece a sí mismo.")
        print()
        print("Cuando el archivo esté lleno, sacale el prefijo `PENDIENTE-` y corré esto.")
        return 0

    for ruta in listos:
        filas = leer_retenido(ruta)
        respondidas = [f for f in filas if f["frase"]]
        print("retenido: %s — %d de %d conjeturas con frase humana"
              % (ruta.name, len(respondidas), len(filas)))
        print()
        aciertos = llegadas = 0
        for f in respondidas:
            r = camino_real.medir(NEUTRA, [f["conjetura"]],
                                  [("x", f["frase"])], AJENOS)
            engancha = r["retenidos"] == 1
            llega = r["retenidos_llegan"] == 1
            aciertos += bool(engancha)
            llegadas += bool(llega)
            print("  [%s%s] %s" % ("SI" if engancha else "no",
                                   "→llega" if llega else "      ", f["frase"][:60]))
            print("       conjetura: %s" % f["conjetura"][:66])
            if r["ajenos"]:
                print("       OJO: esta conjetura engancha %d prompt(s) ajeno(s)" % r["ajenos"])
        print()
        print("=" * 78)
        if respondidas:
            print("SENSIBILIDAD: %d de %d (%.0f%%)."
                  % (aciertos, len(respondidas), 100 * aciertos / len(respondidas)))
            print("Y LO QUE LLEGA AL AGENTE: %d de %d — los que además pasan la compuerta"
                  % (llegadas, len(respondidas)))
            print("del clasificador (`classify_task` distinto de `general`).")
            print("Referencia: el retenido de `cbbd7ff0`, con el prompt viejo, dio 27% de")
            print("ranking y 0% de llegada.")
            print("Es una comparación entre corpus distintos, así que no es un antes/después")
            print("limpio: dice el orden de magnitud, no la mejora.")
        print("=" * 78)
    return 0


if __name__ == "__main__":
    sys.exit(main())
