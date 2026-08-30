"""La expansión asimétrica: el modelo traduce de noche lo que el enganche no traduce.

Enmienda 0.3.13, decidida por Matías el 2026-08-30. El diagnóstico que la motiva está
medido: `experimentos/RESULTADOS-DOMINIOS.md` — la máquina **comprende cuando guarda y
cuenta tokens cuando busca**, así que un síntoma dicho con otro vocabulario no engancha
aunque la memoria hable exactamente de eso (2 de 12, con 10 de los 12 compartiendo una
palabra o ninguna).

`colloquial_queries` mueve la traducción a la noche, que es donde el costo de latencia es
cero: el consolidador escribe cómo lo diría quien lo sufre, y el enganche —que sigue
siendo léxico y sigue siendo determinista— compara contra eso.

**Lo que estos tests fijan es el mecanismo, no el beneficio.** Que el beneficio exista lo
mide `experimentos/17-los-seis-dominios-compiten.py`, y un test no puede decidirlo.
"""

from tests.base import IsolatedStoreTest


class ValidacionDelCampo(IsolatedStoreTest):
    """`colloquial_queries` pasa los mismos gates que todo lo que escribe el modelo."""

    def _validar(self, data, **kw):
        from nightshift import dream, redact
        red = redact.Redactor(identifiers=[], deny_paths=[], home_dir=None)
        return dream.validate(data, redactor=red, home_dir=None, **kw)

    def _base(self, **extra):
        datos = {"pattern": "Un recurso compartido se agota y cada pantalla traduce la "
                            "espera a su propia apariencia local.",
                 "signals": ["el conjunto compartido se agota bajo carga"],
                 "physical_scene": (
                     "En el galpon hay veinte carretillas y cada peon toma una para "
                     "cruzar el patio y la devuelve al volver, salvo uno que la deja "
                     "cargada contra la pared y se va a almorzar. A media manana no "
                     "queda ninguna libre y la fila de peones espera sin que nadie "
                     "entienda por que, porque las carretillas siguen ahi, a la vista, "
                     "apoyadas y quietas contra la pared del fondo."),
                 "logogram": "prestado y nunca devuelto"}
        datos.update(extra)
        return datos

    def test_las_frases_coloquiales_sobreviven_a_validate(self):
        abstraction, _, _, problemas = self._validar(self._base(
            colloquial_queries=["el boton de imprimir esta gris y no se puede apretar",
                                "la app del celular se queda cargando y no carga nunca"]))
        self.assertEqual(problemas, [])
        self.assertEqual(len(abstraction["colloquial_queries"]), 2)

    def test_una_fuga_en_una_frase_coloquial_voltea_la_consolidacion(self):
        """Es texto de modelo y se persiste: no puede tener una puerta propia.

        Y es el campo con más riesgo de los que existen: se le pide al modelo que use
        jerga concreta, y la jerga concreta es exactamente donde alguien escribe una ruta.
        """
        _, _, _, problemas = self._validar(self._base(
            colloquial_queries=["me explota al leer ~/.ssh/id_rsa y no se por que"]))
        self.assertTrue(problemas, "una ruta en una frase coloquial tiene que rechazar")
        self.assertTrue(any("colloquial_queries" in p for p in problemas),
                        "el motivo tiene que nombrar el campo: %s" % problemas)

    def test_el_tope_es_el_mismo_que_el_de_las_senales(self):
        from nightshift import dream
        abstraction, _, _, _ = self._validar(self._base(
            colloquial_queries=["frase numero %d de las que sufre alguien" % i
                                for i in range(12)]))
        self.assertEqual(len(abstraction["colloquial_queries"]), dream.MAX_SIGNALS)

    def test_sin_el_campo_la_abstraccion_sigue_siendo_valida(self):
        """El campo es opcional: una consolidación vieja no deja de valer."""
        abstraction, _, _, problemas = self._validar(self._base())
        self.assertEqual(problemas, [])
        self.assertNotIn("colloquial_queries", abstraction)


class EngancheColoquial(IsolatedStoreTest):
    """El enganche por la superficie nueva, por el camino real de `retrieve`."""

    REPO = "e" * 64

    def setUp(self):
        super().setUp()
        from nightshift import store
        self.conn = store.connect()

    def tearDown(self):
        self.conn.close()
        super().tearDown()

    def _candidata(self, *, signals, coloquiales=None):
        from nightshift import store
        tid = store.open_trajectory(self.conn, session_id="s", repo_fingerprint=self.REPO,
                                    task_type="debug_test_failure", base_commit="abc1234",
                                    redaction={"redactor_version": "0.1.0"})
        store.append_step(self.conn, tid, kind="tool_failure", tool="run_shell",
                          error_message="algo se rompio lejos de la causa", decisive=True)
        store.close_trajectory(self.conn, tid, result="tests_passed")
        abstraccion = {"pattern": "Un mecanismo que se manifiesta lejos de donde actua, "
                                  "descrito en terminos estructurales.",
                       "signals": signals}
        if coloquiales:
            abstraccion["colloquial_queries"] = coloquiales
        store.promote_to_candidate(self.conn, tid, abstraction=abstraccion,
                                   valid_when=[], hypothesis=None, weight=0.6)
        return tid

    def _motivos(self, prompt):
        from nightshift import config, retrieve
        scored = retrieve.candidates(self.conn, task_type="debug_test_failure",
                                     repo_fingerprint=self.REPO, cfg=config.load(),
                                     prompt=prompt)
        return scored[0][1] if scored else ""

    # El par que define el experimento: la señal abstracta y la queja concreta hablan del
    # mismo mecanismo y **no comparten ninguna palabra de contenido**. Es el caso medido
    # en los seis dominios, reducido a dos frases.
    SENAL = "una copia derivada se consulta en lugar de la fuente y nada la refresca"
    QUEJA = "guarde el cambio y la pantalla me sigue mostrando el valor viejo"

    def test_sin_frases_coloquiales_la_queja_no_engancha(self):
        """El estado del que se parte. Si este test se pone verde solo, el experimento
        dejó de medir lo que dice medir."""
        self._candidata(signals=[self.SENAL])
        motivos = self._motivos(self.QUEJA)
        self.assertNotIn("signal_match", motivos)
        self.assertNotIn("colloquial_match", motivos)

    def test_con_frases_coloquiales_la_misma_queja_engancha(self):
        self._candidata(signals=[self.SENAL], coloquiales=[self.QUEJA])
        self.assertIn("colloquial_match", self._motivos(self.QUEJA))

    def test_el_motivo_es_propio_y_no_se_disfraza_de_signal_match(self):
        """`why` tiene que poder decir por dónde entró. Un enganche que se atribuye a la
        superficie equivocada es una explicación falsa, y explicar es la capacidad D."""
        self._candidata(signals=[self.SENAL], coloquiales=[self.QUEJA])
        motivos = self._motivos(self.QUEJA)
        self.assertIn("colloquial_match", motivos)
        self.assertNotIn("signal_match", motivos)

    def test_el_piso_sigue_siendo_dos(self):
        """Una sola palabra en común no alcanza, tampoco acá. La superficie nueva no
        puede traer una regla de enganche más floja que las que ya existen."""
        self._candidata(signals=[self.SENAL],
                        coloquiales=["el informe sale en blanco a la manana"])
        self.assertNotIn("colloquial_match", self._motivos("la pantalla vieja"))

    def test_un_prompt_ajeno_no_engancha_por_la_superficie_nueva(self):
        self._candidata(signals=[self.SENAL], coloquiales=[self.QUEJA])
        motivos = self._motivos("necesito agregar una columna a la tabla de facturas")
        self.assertNotIn("colloquial_match", motivos)
