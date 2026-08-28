"""La escena antes del diagrama — el segundo modo de ideación (ADR-007).

ADR-004 pidió idear como **diagrama Mermaid**. `experimentos/07` midió ese brazo contra un
conjunto retenido y el resultado no lo sostiene: engancha un síntoma más que el control y
lo paga con un prompt ajeno (H17, `FAIL`). La objeción que abre este modo es sobre el
medio, no sobre la idea: un flowchart es **topología** —cajas y flechas— y para el modelo
sigue siendo el mismo campo semántico del código. Cajas genéricas se parecen a demasiadas
cosas.

El modo `fisica` cambia el medio: primero una **escena física** —una máquina, un fluido, un
objeto con peso— y después un **logograma**, dos a cuatro palabras que comprimen el
mecanismo entero como lo hace un pictograma.

Lo que estos tests defienden es lo único que separa esto de un deseo escrito en un prompt:

1. **La escena tiene que ser física de verdad.** Si nombra el dominio del software, no se
   fue a ningún lado: es la misma prosa con otro título, y se rechaza como una fuga.
2. **El logograma se muestra y NO se busca.** Meterlo en la superficie de búsqueda sería
   agregar superficie, que es exactamente lo que H17 castigó, y cambiaría el tratamiento
   sin dejar constancia (PREREG §2).
3. **Ningún modo apaga la ideación.** `fisica` es otro medio, no una salida (H14).
"""

import unittest

from tests.base import IsolatedStoreTest
from nightshift import config, dream, redact, retrieve, store

FP = "f" * 64

# Una escena que se fue de veras al plano físico: pesos, sellos, una balanza. No nombra
# nada del dominio del software y se entiende sin saber qué se estaba arreglando.
ESCENA = ("Una cinta transportadora lleva cajas selladas hasta una balanza que decide si "
          "cada una sigue viaje. La balanza pesa la caja entera, sin abrirla, y una caja "
          "vacía pesa lo mismo que una caja llena de aire. Cuando el llenado falla y la "
          "caja sale vacía, el sello se coloca igual y la balanza la aprueba: nadie mira "
          "adentro hasta el final de la línea, donde ya no se sabe en qué tramo se vació.")

LOGOGRAMA = "caja sellada vacia"


def _redactor():
    return redact.Redactor(identifiers=[], deny_paths=config.DEFAULT_DENY_PATHS,
                           home_dir=None)


def _sembrar(conn, *, task_type="debug_test_failure"):
    tid = store.open_trajectory(conn, session_id="vieja", repo_fingerprint=FP,
                                task_type=task_type, base_commit="abc1234",
                                redaction={"redactor_version": "0.1.0"})
    store.append_step(conn, tid, kind="tool_failure", tool="run_shell",
                      error_message="AssertionError en el borde", decisive=True)
    store.close_trajectory(conn, tid, result="tests_passed")
    return tid


class EscenaFisicaTest(IsolatedStoreTest):
    """El gate que hace real la palabra «física».

    Sin esto, «traducí a una escena física» es un pedido, y un pedido no es un gate
    (CLAUDE.md regla 2). El modelo puede contestar con la misma explicación de siempre
    encabezada por «imaginá una máquina» y nada lo notaría.
    """

    def test_una_escena_fisica_pasa(self):
        self.assertEqual(dream.validate_scene(ESCENA), [])

    def test_una_escena_que_nombra_el_dominio_no_se_fue_a_ningun_lado(self):
        """El caso que este gate existe para atrapar: prosa de software con otro título."""
        problemas = dream.validate_scene(
            "Imaginá una máquina donde la función de validación recibe un archivo y no "
            "revisa su contenido, así que el test pasa igual y el error aparece después.")
        self.assertTrue(problemas)
        self.assertTrue([p for p in problemas if "función" in p or "archivo" in p
                         or "test" in p])

    def test_un_identificador_delata_que_no_hubo_traduccion(self):
        self.assertTrue(dream.validate_scene(
            "Una cinta lleva cajas hasta build_prompt, que las pesa de a una y las deja "
            "pasar sin abrirlas, y al final de la linea nadie sabe cual venia vacia."))

    def test_una_escena_de_una_linea_no_es_una_escena(self):
        """Una imagen que no se puede recorrer no muestra dónde se pierde algo."""
        self.assertTrue(dream.validate_scene("Una caja vacía."))

    def test_una_escena_rota_no_llega_a_candidate(self):
        """Entra por el mismo camino que una fuga: rechazo y el bucle reintenta."""
        _, _, _, problemas = dream.validate(
            {"pattern": "Una etapa sella el resultado sin mirar lo que quedó adentro.",
             "physical_scene": "Una caja vacía.", "logogram": LOGOGRAMA},
            redactor=_redactor(), home_dir=None, modo="fisica")
        self.assertTrue([p for p in problemas if p.startswith("physical_scene:")])

    def test_la_escena_pasa_los_mismos_gates_de_fuga_que_el_resto(self):
        """Es texto de modelo y se persiste: una ruta adentro es una fuga igual."""
        escena = ESCENA + " La balanza está atornillada en /Users/alguien/taller/banco."
        _, _, _, problemas = dream.validate(
            {"pattern": "Una etapa sella el resultado sin mirar lo que quedó adentro.",
             "physical_scene": escena, "logogram": LOGOGRAMA},
            redactor=_redactor(), home_dir=None, modo="fisica")
        self.assertTrue(problemas)


class LogogramaTest(IsolatedStoreTest):
    """Dos a cuatro palabras que comprimen el mecanismo entero.

    La analogía es el pictograma: un signo que no describe la escena, la **nombra**. Si se
    estira a una oración deja de comprimir, y si se encoge a una palabra no dice qué le
    pasa a qué.
    """

    def test_un_logograma_de_dos_a_cuatro_palabras_pasa(self):
        self.assertEqual(dream.validate_logogram(LOGOGRAMA), [])
        self.assertEqual(dream.validate_logogram("centinela ciego"), [])

    def test_una_oracion_no_es_un_logograma(self):
        self.assertTrue(dream.validate_logogram(
            "una caja que se sella vacia y pesa igual que una llena"))

    def test_una_sola_palabra_no_comprime_nada(self):
        self.assertTrue(dream.validate_logogram("caja"))

    def test_un_logograma_no_nombra_la_herramienta(self):
        """Un nombre propio de herramienta engancha con cualquier problema de esa
        herramienta: es la misma regla medida el 2026-08-28 para las señales."""
        self.assertTrue(dream.validate_logogram("linter vacio"))


class BrazoFisicoTest(IsolatedStoreTest):
    """`fisica` es otro medio de idear, nunca una forma de no idear."""

    def test_ningun_modo_apaga_la_ideacion(self):
        conn = store.connect()
        grupo = [store.get_trajectory(conn, _sembrar(conn))]
        for modo in dream.MODOS_DE_IDEACION:
            prompt = dream.build_prompt(conn, grupo, modo=modo)
            self.assertIn("IDEÁ", prompt, "el modo %s no pide idear" % modo)
        conn.close()

    def test_el_brazo_fisico_no_pide_un_diagrama(self):
        """Si pidiera los dos, el experimento compararía acumulación de superficie y no
        dos medios. Un brazo que suma texto engancha más de las dos cosas — es
        literalmente lo que midió H17."""
        conn = store.connect()
        grupo = [store.get_trajectory(conn, _sembrar(conn))]
        fisica = dream.build_prompt(conn, grupo, modo="fisica")
        mermaid = dream.build_prompt(conn, grupo, modo="mermaid")
        conn.close()
        self.assertNotIn("Mermaid", fisica)
        self.assertIn("Mermaid", mermaid)
        self.assertIn("physical_scene", fisica)
        self.assertIn("logogram", fisica)

    def test_en_modo_fisico_un_diagrama_no_se_guarda(self):
        """El modelo puede devolverlo igual; el brazo lo descarta para que los dos brazos
        se diferencien en el medio y no en cuánto texto acumulan."""
        abstraction, _, _, problemas = dream.validate(
            {"pattern": "Una etapa sella el resultado sin mirar lo que quedó adentro.",
             "physical_scene": ESCENA, "logogram": LOGOGRAMA,
             "diagram": "flowchart LR\n  A[caja] --> B[balanza]"},
            redactor=_redactor(), home_dir=None, modo="fisica")
        self.assertEqual(problemas, [])
        self.assertNotIn("_diagram", abstraction)
        self.assertEqual(abstraction["_physical_scene"], ESCENA)
        self.assertEqual(abstraction["_logogram"], LOGOGRAMA)

    def test_consolidate_en_modo_fisico_persiste_la_escena_y_el_logograma(self):
        conn = store.connect()
        _sembrar(conn)

        class Modelo:
            name = "fake"

            def ask_json(self, prompt):
                assert "physical_scene" in prompt, "no llegó el prompt del brazo físico"
                return {"pattern": "Una etapa sella el resultado sin mirar el contenido.",
                        "signals": ["el resumen dice que salio bien y no conto ninguna"],
                        "physical_scene": ESCENA, "logogram": LOGOGRAMA}

        rep = dream.consolidate(conn, Modelo(), cfg=config.load(), lookback_days=3650,
                                modo="fisica")
        self.assertEqual(rep["strategy"], "ideate:fisica")
        fila = conn.execute("SELECT * FROM trajectories WHERE status = 'candidate'"
                            ).fetchone()
        conn.close()
        self.assertEqual(fila["physical_scene"], ESCENA)
        self.assertEqual(fila["logogram"], LOGOGRAMA)


class SeMuestraNoSeBuscaTest(IsolatedStoreTest):
    """La decisión que este modo NO toma: cambiar el ranking.

    El logograma es una compresión, y contra una compresión el enganche por palabras
    funciona peor que contra un síntoma, no mejor: `signals` está escrito con las palabras
    de quien sufre el problema, y el logograma con las de quien lo entendió. Evocar un
    logograma desde el prompt necesitaría embeddings, que chocan con ADR-003.

    Así que entra donde sí sirve —el bloque que lee el agente— y **no** en la superficie de
    búsqueda. Cambiar eso es spec, y con el store creciendo el enganche ya discrimina menos
    (`experimentos/13`), no más.
    """

    def _candidata(self, conn):
        tid = _sembrar(conn)
        store.promote_to_candidate(
            conn, tid,
            abstraction={"pattern": "Una etapa sella el resultado sin mirar el contenido.",
                         "signals": ["la corrida termina en verde y no proceso ni un caso"]},
            valid_when=[], hypothesis=None, weight=0.6,
            physical_scene=ESCENA, logogram=LOGOGRAMA)
        return tid

    def test_la_inyeccion_muestra_la_escena_y_el_logograma(self):
        conn = store.connect()
        tid = self._candidata(conn)
        row = store.get_trajectory(conn, tid)
        texto, _ = retrieve.render(conn, [(2.0, "same_repo", row)], max_injected=3,
                                   native_memory=None, task_type=row["task_type"],
                                   repo_fingerprint=FP)
        conn.close()
        self.assertIn(LOGOGRAMA, texto)
        self.assertIn("cinta transportadora", texto)

    def test_el_logograma_no_es_superficie_de_busqueda(self):
        """Un prompt que sólo comparte palabras con el logograma no engancha.

        Si esto cambia, el tratamiento del experimento cambió y hay que decirlo en la spec
        antes que en el código.
        """
        conn = store.connect()
        tid = self._candidata(conn)
        row = store.get_trajectory(conn, tid)
        scored = retrieve.candidates(conn, task_type=row["task_type"],
                                     repo_fingerprint=FP, cfg=config.load(),
                                     prompt="tengo una caja sellada vacia en la balanza")
        conn.close()
        motivos = scored[0][1] if scored else ""
        self.assertNotIn("signal_match", motivos,
                         "enganchó contra el logograma: eso es cambiar el tratamiento")


if __name__ == "__main__":
    unittest.main()
