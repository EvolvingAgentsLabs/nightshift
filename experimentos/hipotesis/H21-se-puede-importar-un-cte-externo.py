"""H21 — Se puede importar una cadena de ejecución generada afuera, sin mezclarla con lo propio."""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _marco import PASS, FAIL, BLOCKED, StoreDesechable, correr_solo

IDEA = 'oraculos'
HIPOTESIS = 'Se puede importar una cadena de ejecución generada afuera, sin mezclarla con lo propio.'

def correr():
    import io, contextlib
    from nightshift import cli, store
    salida = io.StringIO()
    with contextlib.redirect_stdout(salida), contextlib.suppress(SystemExit):
        cli.main(["--help"])
    if "import" in salida.getvalue():
        with StoreDesechable() as d:
            columnas = {f["name"] for f in d.conn.execute("PRAGMA table_info(trajectories)")}
        if "origin" in columnas:
            return PASS, "existe `import` y la clase de origen"
        return FAIL, "hay `import` y no hay clase de origen: lo externo se mezcla con lo propio"
    return FAIL, ("`export` emite trajectory.v1 y no hay `import`. La plomeria es facil;\n"
                  "lo dificil son dos cosas:\n"
                  "1) PROCEDENCIA. Una trayectoria importada no se observo aca, el redactor\n"
                  "   no corrio sobre ella aca, y nada de lo que afirma es comprobable\n"
                  "   desde esta maquina. Con los mismos pesos, la jerarquia observado >\n"
                  "   inferido > conjeturado se colapsa.\n"
                  "2) Un CoT externo NO es un CTE: no ejecuto. Meterlo como cadena de\n"
                  "   ejecucion es el fallo de la candidata `1f94f424` institucionalizado.\n"
                  "Cuanto pesa lo externo es DECISION DE MATIAS, no de un agente.\n"
                  "Es O4 del plan §7.")

if __name__ == "__main__":
    sys.exit(correr_solo(sys.modules[__name__]))
