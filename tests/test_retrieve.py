"""Retrieval e inyección (M2), y el gate de M2: `why` reconstruye el origen."""

import re
import unittest

from tests.base import IsolatedStoreTest
from nightshift import config, hook, redact, retrieve, store

FP = "f" * 64


class RetrieveTest(IsolatedStoreTest):
    def seed(self, *, task_type="debug_test_failure", fingerprint=FP, result="tests_passed",
             decisive=True, error="UnicodeDecodeError en el borde"):
        conn = store.connect()
        try:
            tid = store.open_trajectory(conn, session_id="vieja", repo_fingerprint=fingerprint,
                                        task_type=task_type, base_commit="abc1234",
                                        redaction={"redactor_version": "0.1.0"})
            store.append_step(conn, tid, kind="tool_failure", tool="run_shell",
                              error_message=error, decisive=decisive)
            store.close_trajectory(conn, tid, result=result)
            return tid
        finally:
            conn.close()

    def fixed_fingerprint(self):
        """Fija el fingerprint del repo para que la sesión de test matchee lo sembrado."""
        import nightshift.context as context
        original = context.repo_fingerprint
        context.repo_fingerprint = lambda cwd: FP

        class _Restore:
            def __enter__(self_inner):
                return self_inner

            def __exit__(self_inner, *exc):
                context.repo_fingerprint = original
                return False

        return _Restore()

    def test_rankea_mismo_tipo_de_tarea_por_encima(self):
        mismo = self.seed(task_type="debug_test_failure")
        otro = self.seed(task_type="docs")
        conn = store.connect()
        try:
            scored = retrieve.candidates(conn, task_type="debug_test_failure",
                                         repo_fingerprint=FP, cfg=config.load())
            ids = [row["id"] for _, _, row in scored]
            self.assertLess(ids.index(mismo), ids.index(otro))
            self.assertIn("same_task_type", dict((r["id"], reason)
                                                 for _, reason, r in scored)[mismo])
        finally:
            conn.close()

    def test_cross_repo_apagado_por_defecto(self):
        self.seed(fingerprint="a" * 64)
        conn = store.connect()
        try:
            cfg = config.load()
            self.assertFalse(cfg["cross_repo"])
            scored = retrieve.candidates(conn, task_type="debug_test_failure",
                                         repo_fingerprint=FP, cfg=cfg)
            self.assertEqual(scored, [], "sin abstracción no se cruza de repo")
        finally:
            conn.close()

    def test_inyeccion_se_registra_y_why_la_reconstruye(self):
        """Gate de M2: toda inyección tiene que ser rastreable a su trayectoria origen."""
        source = self.seed()
        conn = store.connect()
        try:
            # La sesión nueva debe compartir fingerprint con la vieja para que aplique.
            conn.execute("UPDATE trajectories SET repo_fingerprint = ?", (FP,))
            conn.commit()
        finally:
            conn.close()

        import nightshift.context as context
        original = context.repo_fingerprint
        context.repo_fingerprint = lambda cwd: FP
        try:
            text, message = hook.dispatch("SessionStart",
                                          {"session_id": "nueva", "cwd": "."})
        finally:
            context.repo_fingerprint = original

        self.assertIn("nightshift", text)
        self.assertIn(source[:8], text, "el texto inyectado debe traer el id de origen")
        self.assertIn("Ninguna está verificada", text)

        conn = store.connect()
        try:
            rows = store.injections_for_session(conn, "nueva")
            self.assertEqual(len(rows), 1)
            self.assertEqual(rows[0]["source_trajectory"], source)
            back = store.injections_of_source(conn, source)
            self.assertEqual(len(back), 1)
            self.assertIsNotNone(store.get_trajectory(conn, source[:8]))
        finally:
            conn.close()

    def test_general_no_cuenta_como_mismo_tipo_de_tarea(self):
        """`general` es "sin clasificar", no un tipo. Contarlo mentía en el `why`."""
        self.seed(task_type="general")
        conn = store.connect()
        try:
            scored = retrieve.candidates(conn, task_type="general", repo_fingerprint=FP,
                                         cfg=config.load())
            self.assertTrue(scored, "sigue siendo candidata por repo y recencia")
            self.assertNotIn("same_task_type", scored[0][1])
        finally:
            conn.close()

    def test_retrieval_por_tipo_de_tarea_en_el_primer_prompt(self):
        """Gate de T2: `SessionStart` no puede rankear por tipo, el primer prompt sí.

        Se siembran tres trayectorias de otro tipo que llenan el cupo de `SessionStart`
        (que sólo puede rankear por repo y recencia) y una de debugging que se queda
        afuera. Cuando el prompt clasifica la tarea, la de debugging entra — y ninguna
        se inyecta dos veces.
        """
        for _ in range(3):
            self.seed(task_type="docs", result="tests_passed")
        debug = self.seed(task_type="debug_test_failure", result="unknown", decisive=False)

        with self.fixed_fingerprint():
            primero, _ = hook.dispatch("SessionStart", {"session_id": "s", "cwd": "."})
            self.assertNotIn(debug[:8], primero, "sin tipo de tarea no puede elegirla")
            self.assertNotIn("same_task_type", primero)

            segundo, mensaje = hook.dispatch("UserPromptSubmit", {
                "session_id": "s", "cwd": ".",
                "user_input": "los tests fallan con UnicodeDecodeError"})

        self.assertIn(debug[:8], segundo, "el prompt clasificó la tarea: ahora sí aplica")
        self.assertIn("debug_test_failure", mensaje)

        conn = store.connect()
        try:
            rows = store.injections_for_session(conn, "s")
            segunda = [r for r in rows if r["source_trajectory"] == debug]
            self.assertEqual(len(segunda), 1)
            self.assertIn("same_task_type", segunda[0]["reason"])
            fuentes = [r["source_trajectory"] for r in rows]
            self.assertEqual(len(fuentes), len(set(fuentes)),
                             "ninguna trayectoria se inyecta dos veces en la misma sesión")
            self.assertEqual(store.active_trajectory(conn, "s")["task_type"],
                             "debug_test_failure")
        finally:
            conn.close()

    def test_no_se_reinyecta_lo_que_ya_se_dijo(self):
        source = self.seed(task_type="debug_test_failure")
        with self.fixed_fingerprint():
            primero, _ = hook.dispatch("SessionStart", {"session_id": "s2", "cwd": "."})
            self.assertIn(source[:8], primero)
            segundo = hook.dispatch("UserPromptSubmit", {
                "session_id": "s2", "cwd": ".",
                "user_input": "los tests fallan con UnicodeDecodeError"})[0]
        self.assertEqual(segundo, "", "ya se había inyectado en SessionStart")
        conn = store.connect()
        try:
            self.assertEqual(len(store.injections_for_session(conn, "s2")), 1)
        finally:
            conn.close()

    def test_solo_inyecta_una_vez_por_sesion_aunque_haya_mas_prompts(self):
        self.seed(task_type="docs")
        debug = self.seed(task_type="debug_test_failure")
        with self.fixed_fingerprint():
            hook.dispatch("SessionStart", {"session_id": "s3", "cwd": "."})
            hook.dispatch("UserPromptSubmit", {"session_id": "s3", "cwd": ".",
                                               "user_input": "los tests fallan"})
            tercero = hook.dispatch("UserPromptSubmit", {
                "session_id": "s3", "cwd": ".",
                "user_input": "y ahora este otro test también falla"})[0]
        self.assertEqual(tercero, "", "el tipo de tarea ya dejó de ser general una vez")
        conn = store.connect()
        try:
            rows = store.injections_for_session(conn, "s3")
            fuentes = [r["source_trajectory"] for r in rows]
            self.assertEqual(len(fuentes), len(set(fuentes)))
            self.assertIn(debug, fuentes)
        finally:
            conn.close()

    def test_de_otro_repo_cruza_el_patron_y_no_los_pasos(self):
        """Spec §4.2 es una regla sobre lo que se emite, no sólo sobre lo que se elige.

        `candidates()` ya exigía abstracción para cruzar de repo. Pero `render()` seguía
        imprimiendo los pasos de esa trayectoria — nombres de archivo, comandos y
        mensajes de error del otro repo — en cuanto alguien encendiera `cross_repo`.
        """
        import json as _json

        ajeno = self.seed(fingerprint="a" * 64)
        conn = store.connect()
        try:
            conn.execute(
                "UPDATE trajectories SET status = 'candidate', abstraction_json = ?,"
                " valid_when_json = ? WHERE id = ?",
                (_json.dumps({"pattern": "el lector no declara codificación y falla en el"
                                         " primer byte no ASCII"}),
                 _json.dumps([{"condition": "la entrada no es ASCII puro",
                               "source": "inferred"}]), ajeno))
            conn.commit()
            cfg = dict(config.load())
            cfg["cross_repo"] = True
            scored = retrieve.candidates(conn, task_type="debug_test_failure",
                                         repo_fingerprint=FP, cfg=cfg)
            self.assertTrue(scored, "con abstracción sí puede cruzar de repo")
            texto, _ = retrieve.render(conn, scored, max_injected=3, native_memory=False,
                                       task_type="debug_test_failure", repo_fingerprint=FP)
        finally:
            conn.close()

        self.assertIn("el lector no declara codificación", texto)
        self.assertIn("de otro repo", texto)
        self.assertNotIn("UnicodeDecodeError en el borde", texto,
                         "el paso crudo del otro repo no puede cruzar")
        self.assertNotIn("señal decisiva", texto)

    def test_del_mismo_repo_sí_se_muestran_los_pasos(self):
        source = self.seed()
        conn = store.connect()
        try:
            scored = retrieve.candidates(conn, task_type="debug_test_failure",
                                         repo_fingerprint=FP, cfg=config.load())
            texto, _ = retrieve.render(conn, scored, max_injected=3, native_memory=False,
                                       task_type="debug_test_failure", repo_fingerprint=FP)
        finally:
            conn.close()
        self.assertIn(source[:8], texto)
        self.assertIn("UnicodeDecodeError en el borde", texto)

    # ------------------------------------------------ enganche por fallo observado
    def sembrar_con_fallo(self, *, error=None, resumen_de_test=None,
                          task_type="debug_test_failure"):
        """Una trayectoria cruda: un fallo observado, o un test decisivo en verde."""
        conn = store.connect()
        try:
            tid = store.open_trajectory(conn, session_id="vieja", repo_fingerprint=FP,
                                        task_type=task_type, base_commit="abc1234",
                                        redaction={"redactor_version": "0.1.0"})
            if error is not None:
                store.append_step(conn, tid, kind="tool_failure", tool="run_shell",
                                  error_message=error, decisive=True)
            if resumen_de_test is not None:
                # Un comando de test que **pasó**: `decisive` lo marca igual (spec §4.3).
                store.append_step(conn, tid, kind="tool_use", tool="run_shell",
                                  result_summary=resumen_de_test, decisive=True)
            store.close_trajectory(conn, tid, result="tests_passed")
            return tid
        finally:
            conn.close()

    def razones(self, prompt, task_type="debug_test_failure"):
        conn = store.connect()
        try:
            scored = retrieve.candidates(conn, task_type=task_type, repo_fingerprint=FP,
                                         cfg=config.load(), prompt=prompt)
            return {row["id"]: (score, reason) for score, reason, row in scored}
        finally:
            conn.close()

    def test_el_fallo_observado_de_una_trayectoria_cruda_engancha(self):
        """La clave de recuperación es lo que se vio, no el tipo de tarea.

        Sin esto, dos prompts que describen síntomas distintos devuelven exactamente el
        mismo orden: medido sobre el store real antes del cambio.
        """
        visto = self.sembrar_con_fallo(error="UnicodeDecodeError al leer el manifiesto")
        otro = self.sembrar_con_fallo(error="conexión rechazada contra el puerto")
        razones = self.razones("vuelve el UnicodeDecodeError leyendo el manifiesto")
        self.assertIn("failure_match", razones[visto][1])
        self.assertNotIn("failure_match", razones[otro][1])
        self.assertGreater(razones[visto][0], razones[otro][0])

    def test_el_sintoma_puede_mas_que_la_recencia(self):
        """Lo que decide es la señal, no cuál se capturó último."""
        viejo = self.sembrar_con_fallo(error="UnicodeDecodeError al leer el manifiesto")
        nuevo = self.sembrar_con_fallo(error="permiso denegado sobre el directorio")
        razones = self.razones("otra vez el UnicodeDecodeError con el manifiesto")
        self.assertGreater(razones[viejo][0], razones[nuevo][0],
                           "una coincidencia de síntoma tiene que ganarle a la recencia")

    def test_un_test_en_verde_no_es_un_enganche(self):
        """`decisive` marca también los tests que pasan: el 38% de los pasos del store real.

        Enganchar contra su salida haría que cualquier prompt que hable de tests coincida
        con todo. El enganche mira fallos, y un test en verde no es un fallo.
        """
        verde = self.sembrar_con_fallo(
            resumen_de_test="Ran 255 tests in 23.139s OK · make check gate: OK")
        razones = self.razones("corré make check, los 255 tests tienen que quedar en OK")
        self.assertNotIn("failure_match", razones[verde][1])

    def test_los_marcadores_del_redactor_no_enganchan(self):
        """`<REPO>`, `<PATH>`, `<SECRET>` son la huella de lo que se borró.

        Aparecen en casi cualquier fallo capturado: contarlos sería hermanar dos
        trayectorias por lo que **no** se guardó.
        """
        fila = self.sembrar_con_fallo(error="no encuentro <REPO><PATH> ni <SECRET>")
        razones = self.razones("el repo tiene un path roto y un secret que no resuelve")
        self.assertNotIn("failure_match", razones[fila][1])

    def test_el_encabezado_del_harness_no_engancha(self):
        """"Exit code 1" está en todos los fallos: es andamiaje, no síntoma."""
        uno = self.sembrar_con_fallo(error="Exit code 1 parse error cerca de done")
        otro = self.sembrar_con_fallo(error="Exit code 1 el manifiesto no valida")
        razones = self.razones("me da exit code 1 y no entiendo por qué")
        self.assertNotIn("failure_match", razones[uno][1])
        self.assertNotIn("failure_match", razones[otro][1])

    def test_la_lista_de_marcadores_sigue_el_paso_del_redactor(self):
        """Si el redactor aprende un marcador nuevo, esta lista tiene que saberlo.

        El test corre el redactor de verdad sobre material sucio y exige que cada
        `<MARCADOR>` que produzca esté excluido del enganche. Sin esto, agregar una regla
        de redacción abre una vía de falsos enganches en silencio.
        """
        red = redact.Redactor(identifiers=["nightshift"], home_dir="/home/x")
        sucio = ("nightshift falló en /usr/local/lib/cosa.py con "
                 "API_TOKEN=abcd1234efgh y ana@ejemplo.com y "
                 + "a" * 40)
        limpio = red.text(sucio)
        marcadores = set(re.findall(r"<([A-Z_]+)>", limpio))
        self.assertTrue(marcadores, "el redactor no produjo ningún marcador: revisá el material")
        for marcador in marcadores:
            self.assertIn(marcador.lower(), retrieve._MARCADORES_DE_REDACCION,
                          "el redactor produce <%s> y el enganche lo contaría como "
                          "contenido" % marcador)

    def test_una_candidata_engancha_por_su_abstraccion_y_no_por_sus_fallos(self):
        """Con abstracción manda la abstracción: es lo destilado, no la instancia."""
        conn = store.connect()
        try:
            tid = store.open_trajectory(conn, session_id="vieja", repo_fingerprint=FP,
                                        task_type="debug_test_failure", base_commit="abc1234",
                                        redaction={"redactor_version": "0.1.0"})
            store.append_step(conn, tid, kind="tool_failure", tool="run_shell",
                              error_message="UnicodeDecodeError al leer el manifiesto",
                              decisive=True)
            store.close_trajectory(conn, tid, result="tests_passed")
            store.promote_to_candidate(
                conn, tid,
                abstraction={"pattern": "un borde binario tratado como texto",
                             "signals": ["el lector asume codificación"],
                             "decisive_signal": "el error aparece sólo con entrada binaria"},
                valid_when=[{"condition": "hay un decodificador implícito",
                             "source": "observed"}])
        finally:
            conn.close()
        razones = self.razones("vuelve el UnicodeDecodeError leyendo el manifiesto")
        self.assertNotIn("failure_match", razones[tid][1])

    def sembrar_candidata(self, *, patron, senales, condiciones):
        conn = store.connect()
        try:
            tid = store.open_trajectory(conn, session_id="vieja", repo_fingerprint=FP,
                                        task_type="debug_test_failure", base_commit="abc1234",
                                        redaction={"redactor_version": "0.1.0"})
            store.append_step(conn, tid, kind="tool_failure", tool="run_shell",
                              error_message="algo que no se parece a nada", decisive=True)
            store.close_trajectory(conn, tid, result="tests_passed")
            store.promote_to_candidate(
                conn, tid,
                abstraction={"pattern": patron, "signals": senales, "decisive_signal": None},
                valid_when=[{"condition": c, "source": "inferred"} for c in condiciones])
            return tid
        finally:
            conn.close()

    def test_la_precondicion_engancha_aunque_el_sintoma_no(self):
        """"Esto aplica acá" es una clave distinta de "esto ya lo vi".

        La precondición es la mitad del valor de conservar lo descartado (spec §4.2): sin
        ella, una alternativa cuya condición describe la situación de enfrente no puntúa.
        """
        aplica = self.sembrar_candidata(
            patron="un limite configurado por debajo del trabajo real",
            senales=["la suite corta antes de terminar"],
            condiciones=["el proceso corre detras de un proxy con timeout propio"])
        otra = self.sembrar_candidata(
            patron="un decodificador implicito",
            senales=["falla en el primer byte"],
            condiciones=["la entrada no es ascii puro"])
        razones = self.razones("esto corre detras de un proxy y no se por que corta")
        self.assertIn("precondition_match", razones[aplica][1])
        self.assertNotIn("precondition_match", razones[otra][1])
        self.assertGreater(razones[aplica][0], razones[otra][0])

    def test_la_precondicion_pesa_menos_que_la_senal_observada(self):
        """Observado > inferido. El orden es la jerarquía de evidencia del proyecto."""
        self.assertLess(retrieve.W_PRECONDITION_MATCH, retrieve.W_SIGNAL_MATCH)
        self.assertGreater(retrieve.W_PRECONDITION_MATCH, retrieve.W_PROJECTED_MATCH)

    # ── El piso del enganche: destilado y crudo no son la misma clase de texto ────────
    # Enmienda 0.3.6. La spec §5.10 midió que dos prompts con síntomas distintos den
    # órdenes distintos —discriminación— y eso quedó verificado. Lo que nunca se midió es
    # lo que hace una persona: describir el síntoma **con sus palabras**. Medido con
    # `experimentos/05-enganche-por-parafrasis.py` sobre las frases reales de la candidata
    # `fff6af83`, el enganche se caía a 3 de 14 paráfrasis con el piso único en 2.

    def test_una_palabra_destilada_ya_no_alcanza_para_enganchar(self):
        """Enmienda 0.3.10, decidida por Matías: el piso de lo destilado subió a 2.

        La 0.3.6 lo había puesto en 1 midiendo contra un store de UNA candidata, y para
        ese store eligió bien. Con el store crecido, `experimentos/13` midió que el piso 1
        era peor en las dos mitades (4 de 17 verdaderos al top-3, 17 de 24 ajenos
        enganchando algo) y el `15` reprodujo los cruces sobre material diseñado. Una
        palabra en común dejó de ser un enganche; dos lo son.
        """
        tid = self.sembrar_candidata(
            patron="la cadena conserva la estructura y pierde el contenido",
            senales=["los pasos llegan sin descripcion"],
            condiciones=[])
        razones = self.razones("ninguna de las acciones que ejecute quedo con descripcion")
        self.assertNotIn("signal_match", razones.get(tid, (0, ""))[1])
        # Con dos palabras de contenido en común, engancha.
        razones = self.razones("los pasos que ejecute quedaron sin descripcion")
        self.assertIn("signal_match", razones[tid][1])

    def test_una_palabra_cruda_no_alcanza(self):
        """Un mensaje de error crudo es mayormente andamiaje del harness.

        Es el caso que spec §5.10 documentó: con el piso en 1, "exit" y "code" hermanaban
        un `parse error` con un error de formateo. Medido sobre el store real de este
        repo, bajar **este** piso a 1 produce un falso positivo y dejarlo en 2, ninguno.
        Por eso el arreglo es que haya dos pisos, no que baje el único que había.
        """
        tid = self.seed(error="ImportError al cargar el modulo de reportes")
        razones = self.razones("tengo un ImportError en otra cosa totalmente distinta")
        self.assertNotIn("failure_match", razones.get(tid, (0, ""))[1])

    def test_el_piso_es_dos_en_todas_las_superficies(self):
        """Enmienda 0.3.10: el piso duro de discriminación estructural es 2.

        La 0.3.6 separó los pisos (destilado 1, crudo 2) midiendo contra una candidata;
        la 0.3.10 los reunió en 2 midiendo contra el store crecido (`experimentos/13`) y
        contra material diseñado (`15`). Si alguien vuelve a bajar uno, este test es el
        que tiene que fallar primero.
        """
        self.assertEqual(retrieve.MIN_TOKENS_DESTILADO, 2)
        self.assertEqual(retrieve.MIN_TOKENS_CRUDO, 2)
        self.assertEqual(retrieve.MIN_TOKENS_LOGOGRAMA, 2)

    def test_un_predicado_de_fallo_no_engancha_solo(self):
        """"Algo falla" es cierto en cualquier prompt de debugging.

        Apareció al bajar el piso de lo destilado a 1: la condición "esa etapa no falla
        ante contenido ausente" enganchaba con "el deploy falla con un certificado ssl
        vencido" por la palabra `falla` y nada más. Es el mismo caso que `Exit code 1`
        (spec §5.10), del lado destilado.
        """
        tid = self.sembrar_candidata(
            patron="una etapa que no valida contenido",
            senales=["la etapa no falla ante contenido ausente"],
            condiciones=["esa etapa no falla ante contenido ausente"])
        motivos = self.razones("el deploy falla con un certificado ssl vencido")\
            .get(tid, (0, ""))[1]
        self.assertNotIn("signal_match", motivos)
        self.assertNotIn("precondition_match", motivos)

    def test_un_predicado_de_fallo_si_suma_como_segunda_palabra(self):
        """No es una palabra vacía: acompañada dice de qué se habla.

        La distinción importa. Sacarla del vocabulario perdería enganches legítimos; lo
        que no puede es sostener uno ella sola.
        """
        tid = self.sembrar_candidata(
            patron="una etapa que no valida contenido",
            senales=["la extraccion falla ante contenido ausente"],
            condiciones=[])
        motivos = self.razones("la extraccion me falla siempre")[tid][1]
        self.assertIn("signal_match", motivos)

    def test_el_control_negativo_sigue_sin_enganchar(self):
        """Bajar un piso sólo sirve si no engancha con cualquier cosa.

        Si estos prompts empiezan a puntuar, el matcher dejó de reconocer síntomas y pasó
        a reconocer texto — que es el fallo que el proyecto ya pagó dos veces.
        """
        tid = self.sembrar_candidata(
            patron="la cadena conserva la estructura y pierde el contenido",
            senales=["los pasos llegan sin descripcion",
                     "el desenlace de cada trayectoria es desconocido"],
            condiciones=["la etapa de extraccion nunca escribe el campo"])
        ajenos = [
            "el css del boton de login quedo desalineado en mobile",
            "el deploy a produccion falla con un error de certificado ssl vencido",
            "quiero renombrar la variable foo a bar en todo el proyecto",
            "como configuro el timezone del servidor",
        ]
        for prompt in ajenos:
            with self.subTest(prompt=prompt):
                motivos = self.razones(prompt).get(tid, (0, ""))[1]
                self.assertNotIn("signal_match", motivos)
                self.assertNotIn("precondition_match", motivos)
                self.assertNotIn("projected_match", motivos)

    def test_sin_historia_no_inyecta_nada(self):
        text, message = hook.dispatch("SessionStart",
                                      {"session_id": "limpia", "cwd": "."})
        self.assertEqual(text, "")
        self.assertIn("sin memoria previa", message)

    def test_trayectoria_abandonada_no_se_inyecta(self):
        self.seed(result="abandoned")
        conn = store.connect()
        try:
            scored = retrieve.candidates(conn, task_type="debug_test_failure",
                                         repo_fingerprint=FP, cfg=config.load())
            self.assertEqual(scored, [], "las descartadas no se inyectan")
        finally:
            conn.close()


if __name__ == "__main__":
    unittest.main()
