"""Ideación y proyección (ADR-004).

Dream deja de mirar sólo para atrás: idea el mecanismo como un dibujo, abstrae desde ahí
y **proyecta** en qué otras formas se va a manifestar. Eso último es lo que hace útil a la
memoria antes de que el síntoma se repita — y es también lo más fácil de convertir en
fabricación.

Por eso casi todos los tests de acá son sobre la misma frontera: **lo proyectado nunca se
confunde con lo observado.** Se guarda aparte, pesa la mitad, y en cada lugar donde
aparece dice que nadie lo vio. Si esa frontera se borra, nightshift deja de ser memoria y
pasa a ser una fuente de afirmaciones sin origen.
"""

import json
import unittest

from tests.base import IsolatedStoreTest
from nightshift import config, context, dream, redact, retrieve, store

FP = "f" * 64


def _redactor():
    return redact.Redactor(identifiers=[], deny_paths=config.DEFAULT_DENY_PATHS,
                           home_dir=None)


def _sembrar(conn, *, task_type="debug_test_failure"):
    tid = store.open_trajectory(conn, session_id="vieja", repo_fingerprint=FP,
                                task_type=task_type, base_commit="abc1234",
                                redaction={"redactor_version": "0.1.0"})
    store.append_step(conn, tid, kind="tool_failure", tool="run_shell",
                      error_message="KeyError en el borde", decisive=True)
    store.close_trajectory(conn, tid, result="tests_passed")
    return tid


class IdeacionTest(IsolatedStoreTest):
    def test_idear_es_el_default_del_prompt(self):
        """Enmienda 0.3.7: idear dejó de ser una rama y pasó a ser el flujo.

        El brazo sin idear sigue existiendo, pero hay que pedirlo: es el control de
        `experimentos/ideate.py`, no una opción alcanzable desde el plugin.
        """
        conn = store.connect()
        tid = _sembrar(conn)
        grupo = [store.get_trajectory(conn, tid)]

        default = dream.build_prompt(conn, grupo)
        control = dream.build_prompt(conn, grupo, ideate=False)

        self.assertIn("IDEÁ", default)
        self.assertNotIn("IDEÁ", control)
        # El cuerpo tiene que ser el mismo: una sola variable entre las dos ramas.
        self.assertTrue(default.endswith(control))

    def test_el_contraste_tambien_idea_por_defecto(self):
        conn = store.connect()
        vieja = store.get_trajectory(conn, _sembrar(conn))
        nueva = store.get_trajectory(conn, _sembrar(conn))
        self.assertIn("IDEÁ", dream.build_contrast_prompt(conn, vieja, nueva))

    def test_no_queda_ninguna_llave_de_config_que_apague_la_ideacion(self):
        """El interruptor que se sacó, y el motivo por el que no puede volver.

        `observed` no produce `projected_signals`. Mientras la estrategia fuera una clave
        de config, la única capacidad que engancha con un problema **antes** de que su
        síntoma se haya visto una vez quedaba detrás de un default.
        """
        self.assertNotIn("consolidation_strategy", config.DEFAULTS)

    def test_consolidate_idea_aunque_la_config_diga_lo_contrario(self):
        """Una config vieja en disco no puede devolver el interruptor por la ventana."""
        conn = store.connect()
        _sembrar(conn)
        cfg = config.load()
        cfg["consolidation_strategy"] = "observed"       # como quedó una config anterior
        vistos = []

        class ModeloQueMiraElPrompt:
            name = "fake"

            def ask_json(self, prompt):
                vistos.append(prompt)
                return {"pattern": "Una etapa valida la forma del registro y nunca su "
                                   "contenido, asi que lo vacio pasa como valido."}

        reporte = dream.consolidate(conn, ModeloQueMiraElPrompt(), cfg=cfg,
                                    lookback_days=3650)
        conn.close()
        self.assertEqual(reporte["strategy"], "ideate")
        self.assertTrue(vistos, "el modelo no llegó a ver ningún prompt")
        self.assertIn("IDEÁ", vistos[0])

    def test_la_ideacion_se_extrae_aunque_venga_escapada(self):
        """El envoltorio del agente trae la respuesta como string JSON.

        Sin deshacer el escape, la ideación se guarda con `\\n` literales adentro — y ese
        texto se inyecta, así que no es cosmético.
        """
        crudo = ('{"result": "<ideacion>Una llave entra' + chr(92) + "n"
                 + 'y sale con otra forma.</ideacion>{}"}')
        self.assertEqual(dream.extract_ideation(crudo),
                         "Una llave entra y sale con otra forma.")
        self.assertIsNone(dream.extract_ideation('{"result": "sin marcas"}'))


class FronteraTest(IsolatedStoreTest):
    """Lo observado y lo anticipado no se mezclan en ningún lado."""

    def _validar(self, data, ideation=None):
        return dream.validate(data, redactor=_redactor(), home_dir=None,
                              ideation=ideation)

    def test_lo_proyectado_no_entra_en_signals(self):
        abstraction, _, _, problemas = self._validar({
            "pattern": "Una función de normalización compartida no cubre un caso.",
            "signals": ["el test falla al comparar dos claves"],
            "projected_signals": ["un reporte suma dos veces el mismo registro"],
        })
        self.assertEqual(problemas, [])
        self.assertEqual(abstraction["signals"], ["el test falla al comparar dos claves"])
        self.assertEqual(abstraction["_projected_signals"],
                         ["un reporte suma dos veces el mismo registro"])

    def test_proyectar_algo_ya_observado_no_proyecta_nada(self):
        """Repetir una señal observada en la lista de proyectadas la duplicaría.

        Y una señal duplicada suma dos veces en el ranking: la observada por su peso y la
        "proyectada" por el suyo, siendo la misma frase.
        """
        abstraction, _, _, _ = self._validar({
            "pattern": "Una función de normalización compartida no cubre un caso.",
            "signals": ["el test falla al comparar dos claves"],
            "projected_signals": ["el test falla al comparar dos claves"],
        })
        self.assertNotIn("_projected_signals", abstraction)

    def test_una_proyeccion_con_fuga_voltea_la_consolidacion(self):
        """Pasa por los mismos gates que todo lo demás: es texto de modelo."""
        _, _, _, problemas = self._validar({
            "pattern": "Una función de normalización compartida no cubre un caso.",
            "projected_signals": ["falla al leer ~/.ssh/id_rsa"],
        })
        self.assertTrue(problemas, "una ruta en una proyección tiene que rechazarse")

    def test_la_ideacion_con_fuga_voltea_la_consolidacion(self):
        _, _, _, problemas = self._validar(
            {"pattern": "Una función de normalización compartida no cubre un caso."},
            ideation="El dato entra por /Users/alguien/proyecto/src y sale deformado.")
        self.assertTrue(problemas, "una ruta en la ideación tiene que rechazarse")


class EngancheTest(IsolatedStoreTest):
    """El retrieval engancha por síntoma, y lo proyectado pesa la mitad."""

    def _sembrar(self, conn, *, proyectadas):
        tid = _sembrar(conn)
        store.promote_to_candidate(
            conn, tid,
            abstraction={"pattern": "El indice se arma normalizando la clave pero la "
                                    "consulta busca con la clave cruda.",
                         "signals": ["una clave que esta en el indice levanta KeyError"]},
            valid_when=[], hypothesis=None, weight=0.6,
            projected_signals=proyectadas)
        return tid

    def _score(self, prompt, *, proyectadas):
        conn = store.connect()
        self._sembrar(conn, proyectadas=proyectadas)
        scored = retrieve.candidates(
            conn, task_type="debug_test_failure",
            repo_fingerprint=FP, cfg=config.load(), prompt=prompt)
        conn.close()
        self.assertTrue(scored, "no rankeó nada")
        return scored[0][0], scored[0][1]

    def test_un_sintoma_observado_engancha(self):
        _, motivos = self._score(
            "el indice levanta KeyError con una clave que esta ahi", proyectadas=None)
        self.assertIn("signal_match", motivos)

    def test_un_sintoma_solo_anticipado_tambien_engancha_pero_menos(self):
        """Éste es el punto de todo el mecanismo: el síntoma NO se vio nunca.

        La trayectoria guardada habla de un `KeyError` en un índice. El prompt habla de
        totales que no cierran en un reporte — otro síntoma, que nadie capturó. Engancha
        porque dream lo anticipó desde el dibujo del mecanismo.
        """
        sin, _ = self._score("los totales del reporte no cierran y un cliente aparece "
                             "duplicado", proyectadas=None)
        con, motivos = self._score(
            "los totales del reporte no cierran y un cliente aparece duplicado",
            proyectadas=["los totales de un reporte no cierran porque un registro "
                         "aparece duplicado"])
        self.assertIn("projected_match", motivos)
        self.assertGreater(con, sin, "la proyección tiene que sumar")

    def test_lo_proyectado_pesa_la_mitad_que_lo_observado(self):
        """No es calibración: una la vio alguien y la otra la anticipó un modelo."""
        self.assertEqual(retrieve.W_PROJECTED_MATCH * 2, retrieve.W_SIGNAL_MATCH)

    def test_una_sola_palabra_en_comun_no_es_un_enganche(self):
        """Con el umbral en 1, "test" hermana cualquier par de trayectorias del repo."""
        self.assertEqual(retrieve._enganche(retrieve._tokens("el test falla"),
                                            ["otro test cualquiera"]), 0)

    def test_sin_prompt_no_hay_enganche(self):
        """`SessionStart` corre antes de que el usuario escriba (spec §5.7).

        Inventar un enganche sin texto sería el mismo error que contar `general` como
        coincidencia de tipo de tarea: parecería estructural sin serlo.
        """
        _, motivos = self._score(None, proyectadas=["cualquier cosa que no se vio"])
        self.assertNotIn("projected_match", motivos)
        self.assertNotIn("signal_match", motivos)


class PrioridadDelEngancheTest(IsolatedStoreTest):
    """La conjetura tiene que llegar **antes** del error, y eso es un problema de orden.

    Medido sobre el store real el 2026-08-27: con un prompt que enganchaba por síntoma
    proyectado, la única fila que hablaba del problema quedaba tercera de tres, detrás de
    dos trayectorias en verde que no compartían una palabra con el prompt.

        1.045  closed     same_repo,has_decisive_step,tests_passed
        1.030  closed     same_repo,has_decisive_step,tests_passed
        1.009  candidate  same_repo,projected_match      <- la única que engancha

    `has_decisive_step` + `tests_passed` son 2,5 puntos que no dependen del prompt. Con
    `max_injected` en 3 la proyección entraba raspando; con una cuarta trayectoria en
    verde en el store se caía de la inyección — y una proyección que no llega antes del
    error no proyectó nada.
    """

    PROYECTADA = ("los totales de un reporte no cierran porque un registro aparece "
                  "duplicado")
    PROMPT = "los totales del reporte no cierran y un cliente aparece duplicado"

    def _sembrar_ruidosas(self, conn, cuantas=3):
        """Trayectorias con puntaje estructural alto y **nada** que ver con el prompt."""
        for i in range(cuantas):
            tid = store.open_trajectory(conn, session_id="ruido%d" % i,
                                        repo_fingerprint=FP,
                                        task_type="debug_test_failure",
                                        base_commit="abc1234",
                                        redaction={"redactor_version": "0.1.0"})
            store.append_step(conn, tid, kind="tool_failure", tool="run_shell",
                              error_message="el decodificador explota en el primer byte",
                              decisive=True)
            store.close_trajectory(conn, tid, result="tests_passed")

    def _sembrar_candidata(self, conn):
        """La que engancha: sin desenlace, sin paso decisivo, y con la conjetura."""
        tid = store.open_trajectory(conn, session_id="candidata", repo_fingerprint=FP,
                                    task_type=context.DEFAULT_TASK_TYPE,
                                    base_commit="abc1234",
                                    redaction={"redactor_version": "0.1.0"})
        store.append_step(conn, tid, kind="tool_use", tool="run_shell",
                          result_summary="se miro el indice", decisive=False)
        store.close_trajectory(conn, tid, result="unknown")
        store.promote_to_candidate(
            conn, tid,
            abstraction={"pattern": "El indice se arma normalizando la clave pero la "
                                    "consulta busca con la clave cruda.",
                         "signals": ["una clave que esta en el indice levanta KeyError"]},
            valid_when=[], hypothesis=None, weight=0.6,
            projected_signals=[self.PROYECTADA])
        return tid

    def _rankear(self, prompt):
        conn = store.connect()
        self._sembrar_ruidosas(conn)
        tid = self._sembrar_candidata(conn)
        scored = retrieve.candidates(conn, task_type="debug_test_failure",
                                     repo_fingerprint=FP, cfg=config.load(),
                                     prompt=prompt)
        conn.close()
        return tid, scored

    def test_la_que_engancha_va_primera_aunque_puntue_menos(self):
        tid, scored = self._rankear(self.PROMPT)
        self.assertEqual(scored[0][2]["id"], tid,
                         "la única fila que habla del problema no quedó primera")
        self.assertIn("projected_match", scored[0][1])
        # Y el punto entero: gana **sin** ganar por puntaje. Si algún día gana por
        # puntaje, este assert falla y hay que releer la regla, no borrarla.
        self.assertLess(scored[0][0], max(item[0] for item in scored[1:]),
                        "si la que engancha ya puntúa más, este test dejó de probar el "
                        "orden y hay que revisar por qué")

    def test_con_una_sola_ranura_la_que_llega_es_la_que_engancha(self):
        """`max_injected` es chico a propósito: el orden decide qué se pierde."""
        conn = store.connect()
        self._sembrar_ruidosas(conn)
        self._sembrar_candidata(conn)
        scored = retrieve.candidates(conn, task_type="debug_test_failure",
                                     repo_fingerprint=FP, cfg=config.load(),
                                     prompt=self.PROMPT)
        texto, chosen = retrieve.render(conn, scored, max_injected=1,
                                        native_memory=False,
                                        task_type="debug_test_failure",
                                        repo_fingerprint=FP)
        conn.close()
        self.assertEqual(len(chosen), 1)
        self.assertIn(self.PROYECTADA, texto)
        self.assertIn("NINGUNO fue observado", texto)
        # El orden dejó de ser sólo por puntaje: el texto tiene que decir por qué.
        self.assertIn("enganchan con lo que acabás de escribir", texto)

    def test_sin_prompt_el_orden_no_cambia(self):
        """`SessionStart` corre antes de que el usuario escriba.

        Ahí no engancha nada, y esta regla no puede reordenar una sola fila: si lo
        hiciera, estaría inventando relevancia sin texto — el mismo error que contar
        `general` como coincidencia de tipo de tarea (spec §5.7).
        """
        _, scored = self._rankear(None)
        self.assertEqual([item[0] for item in scored],
                         sorted((item[0] for item in scored), reverse=True))


class InyeccionTest(IsolatedStoreTest):
    def test_la_inyeccion_dice_que_lo_anticipado_no_se_observo(self):
        """Si el agente no puede distinguirlo, dream deja de ser memoria."""
        conn = store.connect()
        tid = _sembrar(conn)
        store.promote_to_candidate(
            conn, tid,
            abstraction={"pattern": "El indice se arma normalizando la clave pero la "
                                    "consulta busca con la clave cruda.",
                         "signals": ["una clave que esta en el indice levanta KeyError"]},
            valid_when=[], hypothesis=None, weight=0.6,
            ideation="Una llave entra, se lima, y despues alguien prueba la llave sin limar.",
            projected_signals=["los totales de un reporte no cierran"])
        scored = retrieve.candidates(conn, task_type="debug_test_failure",
                                     repo_fingerprint=FP, cfg=config.load())
        texto, chosen = retrieve.render(conn, scored, max_injected=3, native_memory=False,
                                        task_type="debug_test_failure",
                                        repo_fingerprint=FP)
        conn.close()
        self.assertTrue(chosen)
        self.assertIn("anticipados", texto)
        self.assertIn("NINGUNO fue observado", texto)
        self.assertIn("qué se conserva y qué se pierde", texto)
        # Y la proyección no puede aparecer presentada como señal observada.
        linea_proyectada = next(l for l in texto.splitlines()
                                if "totales de un reporte" in l)
        self.assertTrue(linea_proyectada.strip().startswith("-"))

    def test_la_ideacion_larga_se_corta_en_una_oracion_entera(self):
        """Medido: el modelo devuelve ~1800 caracteres para "tres a seis oraciones".

        Inyectada entera gasta más contexto que las tres trayectorias juntas. Y cortar a
        la mitad de una frase deja un dibujo peor que uno más corto.
        """
        largo = ("Una llave entra y se lima. " * 40).strip()
        corto = retrieve._recortar(largo)
        self.assertLess(len(corto), len(largo))
        self.assertIn("why", corto)
        self.assertTrue(corto.split(" […]")[0].endswith("."),
                        "tiene que cortar en punto: %r" % corto[-40:])

    def test_el_diagrama_se_inyecta_entero_y_como_mermaid(self):
        """Un diagrama es dibujo y texto a la vez: recortarlo no lo achica, lo rompe.

        Y va en un bloque `mermaid` porque ahí es donde se renderiza. El tope de nodos se
        pide en el prompt, que es donde se puede pedir brevedad sin romper la sintaxis.
        """
        conn = store.connect()
        tid = _sembrar(conn)
        diagrama = ("flowchart LR\n"
                    "  A[clave cruda] -->|se normaliza| B[clave limada]\n"
                    "  B --> C[(indice)]\n"
                    "  A -->|consulta sin limar| C")
        store.promote_to_candidate(
            conn, tid, abstraction={"pattern": "El indice se arma con la clave "
                                               "normalizada y se consulta con la cruda."},
            valid_when=[], hypothesis=None, weight=0.6, diagram=diagrama)
        scored = retrieve.candidates(conn, task_type="debug_test_failure",
                                     repo_fingerprint=FP, cfg=config.load())
        texto, _ = retrieve.render(conn, scored, max_injected=3, native_memory=False,
                                   task_type="debug_test_failure", repo_fingerprint=FP)
        conn.close()
        self.assertIn("```mermaid", texto)
        for linea in diagrama.splitlines():
            self.assertIn(linea, texto, "el diagrama llegó cortado")

    def test_un_diagrama_con_una_ruta_voltea_la_consolidacion(self):
        """Las etiquetas de un flowchart son justo donde alguien escribe una ruta."""
        _, _, _, problemas = dream.validate(
            {"pattern": "Una funcion de normalizacion compartida no cubre un caso.",
             "diagram": "flowchart LR\n  A[/Users/alguien/proyecto/src] --> B[salida]"},
            redactor=_redactor(), home_dir=None)
        self.assertTrue(problemas, "una ruta en el diagrama tiene que rechazarse")

    def test_una_fila_vieja_sin_la_columna_no_rompe_nada(self):
        """La columna llega por migración: hay candidates consolidadas antes de ADR-004."""
        conn = store.connect()
        tid = _sembrar(conn)
        store.promote_to_candidate(
            conn, tid, abstraction={"pattern": "Un patron cualquiera que sirve de prueba."},
            valid_when=[], hypothesis=None, weight=0.6)
        row = store.get_trajectory(conn, tid)
        conn.close()
        self.assertEqual(retrieve._proyectadas(row), [])


if __name__ == "__main__":
    unittest.main()
