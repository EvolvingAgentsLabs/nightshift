"""Scheduler pluggable (M3-b) y el registro de corridas.

Ningún test de acá carga nada en launchd ni en systemd: se instala con `--no-activate`
y con `HOME` apuntando a un directorio temporal. Un test que llame a `launchctl` de
verdad le deja un job instalado a quien lo corra, y eso no es un test, es un efecto.

El gate de T5 es `test_status_reporta_las_ultimas_corridas_y_sus_resultados`. El gate
real de M3 — tres noches seguidas sin intervención — lo corre una persona; esto es lo que
lo hace verificable.
"""

import contextlib
import io
import json
import os
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

from tests.base import IsolatedStoreTest
from nightshift import cli, config, schedule, store


class ScheduleTest(IsolatedStoreTest):
    def setUp(self):
        super().setUp()
        # `Path.home()` respeta $HOME: así las unidades se escriben en un temporal y no
        # en ~/Library/LaunchAgents del usuario que corre los tests.
        self._fake_home = tempfile.TemporaryDirectory(prefix="nightshift-home-")
        self._saved_home = os.environ.get("HOME")
        os.environ["HOME"] = self._fake_home.name

    def tearDown(self):
        if self._saved_home is None:
            os.environ.pop("HOME", None)
        else:
            os.environ["HOME"] = self._saved_home
        self._fake_home.cleanup()
        super().tearDown()

    def run_cli(self, argv):
        out, err = io.StringIO(), io.StringIO()
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
            code = cli.main(argv)
        return code, out.getvalue(), err.getvalue()

    def seed_run(self, **kwargs):
        conn = store.connect()
        try:
            store.record_run(conn, **kwargs)
        finally:
            conn.close()

    # ------------------------------------------------------------- el gate de T5
    def test_status_reporta_las_ultimas_corridas_y_sus_resultados(self):
        self.seed_run(command="dream", backend="launchd", exit_code=0, trajectories=4,
                      candidates=2, superseded=1, rejected=0)
        self.seed_run(command="dream", backend="launchd", exit_code=2,
                      note="no hay modelo local disponible")
        self.run_cli(["schedule", "install", "--backend", "launchd", "--no-activate"])

        code, out, _ = self.run_cli(["schedule", "status"])

        self.assertEqual(code, 0, "con el timer instalado, status sale 0")
        self.assertIn("cand=2", out)
        self.assertIn("sup=1", out)
        self.assertIn("ok", out)
        self.assertIn("sin modelo local", out, "una corrida fallida también es un resultado")
        self.assertIn("launchd", out)

    def test_sin_corridas_lo_dice_en_vez_de_mentir(self):
        self.run_cli(["schedule", "install", "--backend", "launchd", "--no-activate"])
        _, out, _ = self.run_cli(["schedule", "status"])
        self.assertIn("ninguna todavía", out)
        self.assertIn("es una promesa", out)

    def test_sin_instalar_status_sale_1(self):
        code, out, _ = self.run_cli(["schedule", "status"])
        self.assertEqual(code, 1)
        self.assertIn("instalado  : no", out)

    def test_status_json(self):
        self.seed_run(command="dream", backend="loop", exit_code=0, candidates=1)
        code, out, _ = self.run_cli(["schedule", "status", "--json"])
        data = json.loads(out)
        self.assertEqual(data["corridas"][0]["candidates"], 1)
        self.assertIn(data["backend_elegido"], schedule.BACKENDS)
        self.assertEqual(code, 1, "todavía no hay nada instalado")

    # ------------------------------------------------------------------ backends
    def test_install_y_uninstall_no_dejan_rastro(self):
        code, out, _ = self.run_cli(["schedule", "install", "--backend", "launchd",
                                     "--no-activate"])
        self.assertEqual(code, 0)
        plist = Path(os.environ["HOME"]) / "Library/LaunchAgents" / ("%s.plist" % schedule.LABEL)
        self.assertTrue(plist.is_file())
        self.assertIn("no activado", out)

        code, out, _ = self.run_cli(["schedule", "uninstall"])
        self.assertEqual(code, 0)
        self.assertFalse(plist.exists())

    def test_dry_run_no_escribe_nada(self):
        code, out, _ = self.run_cli(["schedule", "install", "--backend", "systemd",
                                     "--dry-run"])
        self.assertEqual(code, 0)
        self.assertIn("OnCalendar=*-*-* 03:30:00", out)
        self.assertFalse((Path(os.environ["HOME"]) / ".config/systemd").exists())

    def test_el_plist_es_un_plist(self):
        if not shutil.which("plutil"):
            self.skipTest("plutil sólo existe en macOS")
        self.run_cli(["schedule", "install", "--backend", "launchd", "--no-activate"])
        plist = Path(os.environ["HOME"]) / "Library/LaunchAgents" / ("%s.plist" % schedule.LABEL)
        result = subprocess.run(["plutil", "-lint", str(plist)], capture_output=True,
                                text=True, timeout=30)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def fake_tool(self, name):
        """Deja un ejecutable falso en el PATH. Sin esto el test de systemd pasaba vacío.

        En macOS no hay `systemctl`, así que `activate()` devolvía la lista vacía y el
        bucle que afirmaba `--user` no se ejecutaba nunca: un test que no puede fallar.
        """
        tmp = tempfile.mkdtemp(prefix="ns-bin-")
        path = Path(tmp) / name
        path.write_text("#!/bin/sh\nexit 0\n", encoding="utf-8")
        path.chmod(0o755)
        saved = os.environ["PATH"]
        os.environ["PATH"] = tmp + os.pathsep + saved
        self.addCleanup(lambda: os.environ.__setitem__("PATH", saved))
        self.addCleanup(lambda: shutil.rmtree(tmp, ignore_errors=True))
        return path

    def test_systemd_es_un_timer_de_usuario(self):
        """Nunca una unidad de sistema (spec §7.1)."""
        self.fake_tool("systemctl")
        backend = schedule.backend("systemd", config.load())
        self.assertIn("/.config/systemd/user/", str(backend.unit_path))
        comandos = backend.activate() + backend.deactivate()
        self.assertTrue(comandos, "sin comandos el test no prueba nada")
        for command in comandos:
            self.assertIn("--user", command)
        self.assertIn("WantedBy=timers.target", backend.render())

    def test_la_corrida_nocturna_usa_caffeinate_si_existe(self):
        backend = schedule.backend("launchd", config.load())
        command = backend.command()
        self.assertIn("dream", command)
        self.assertIn("--backend", command)
        if shutil.which("caffeinate"):
            self.assertIn("caffeinate", command[0],
                          "un equipo dormido a mitad de la consolidación no la termina")

    def test_el_comando_no_depende_del_PATH_interactivo(self):
        """launchd y systemd corren con un entorno mínimo."""
        backend = schedule.backend("loop", config.load())
        binario = [p for p in backend.command() if p.endswith("nightshift")][0]
        self.assertTrue(Path(binario).is_absolute())

    def test_autodeteccion_y_backend_fijado(self):
        self.assertEqual(schedule.detect({"scheduler_backend": "loop"}), "loop")
        self.assertIn(schedule.detect({"scheduler_backend": "auto"}), schedule.BACKENDS)

    def test_un_backend_desconocido_no_se_instala(self):
        with self.assertRaises(ValueError):
            schedule.resolve("cron", config.load())

    # --------------------------------------------------- registro de las corridas
    def test_dream_deja_su_corrida_registrada(self):
        code, _, _ = self.run_cli(["dream", "--model", "/bin/echo", "--backend", "launchd"])
        self.assertEqual(code, 0, "sin trayectorias no hay nada que consolidar")
        conn = store.connect()
        try:
            runs = store.recent_runs(conn)
        finally:
            conn.close()
        self.assertEqual(len(runs), 1)
        self.assertEqual(runs[0]["backend"], "launchd")
        self.assertEqual(runs[0]["exit_code"], 0)
        self.assertIn("nada que consolidar", runs[0]["note"])

    def test_sin_modelo_detectado_no_se_toca_el_store(self):
        from nightshift import dream

        original = dream.detect_command
        dream.detect_command = lambda cfg: None
        try:
            code, _, _ = self.run_cli(["dream"])
        finally:
            dream.detect_command = original
        self.assertEqual(code, 2)
        conn = store.connect()
        try:
            runs = store.recent_runs(conn)
        finally:
            conn.close()
        self.assertEqual(runs, [], "si no hay modelo ni se abre el store")

    def test_el_error_del_modelo_se_redacta_antes_de_guardarse(self):
        """Un mensaje de error es texto no controlado como cualquier otro."""
        conn = store.connect()
        try:
            tid = store.open_trajectory(conn, session_id="x", repo_fingerprint="f" * 64,
                                        task_type="general")
            store.append_step(conn, tid, kind="tool_use", tool="run_shell",
                              result_summary="la suite pasa")
            store.close_trajectory(conn, tid, result="tests_passed")
        finally:
            conn.close()

        code, _, _ = self.run_cli(["dream", "--model", "/nonexistent/modelo-fantasma"])
        self.assertEqual(code, 2, "el binario del modelo no existe")

        conn = store.connect()
        try:
            nota = store.recent_runs(conn)[0]["note"]
        finally:
            conn.close()
        self.assertIsNotNone(nota, "una corrida fallida es un resultado, se registra")
        self.assertNotIn("modelo-fantasma", nota, "la ruta no se guarda en claro")
        self.assertIn("<PATH>", nota)

        # Y el auditor de M1 tiene que seguir sin encontrar nada en el store.
        code, _, _ = self.run_cli(["audit"])
        self.assertEqual(code, 0)

    def test_loop_una_vuelta_y_sale(self):
        code, out, _ = self.run_cli(["schedule", "loop", "--once", "--backend", "loop"])
        self.assertIn("dream salió", out)
        self.assertEqual(code, 0)
        conn = store.connect()
        try:
            self.assertEqual(store.recent_runs(conn)[0]["backend"], "loop")
        finally:
            conn.close()


if __name__ == "__main__":
    unittest.main()
