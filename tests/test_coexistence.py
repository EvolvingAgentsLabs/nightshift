"""Coexistencia con Auto Memory: condición de éxito 4 de la spec.

No se promete, se testea: una sesión completa no puede dejar una sola escritura bajo
el árbol de Auto Memory.
"""

import os
import unittest
from pathlib import Path

from tests.base import IsolatedStoreTest
from nightshift import config, hook


class CoexistenceTest(IsolatedStoreTest):
    def test_guard_rechaza_el_arbol_de_auto_memory(self):
        for bad in ("/home/x/.claude/projects/-home-x-proj/memory/MEMORY.md",
                    "/home/x/.claude/projects/abc/memory",
                    "/Users/x/.claude/projects/p/memory/notes.md"):
            with self.subTest(bad=bad):
                with self.assertRaises(PermissionError):
                    config.guard_path(Path(bad))

    def test_guard_permite_rutas_normales(self):
        config.guard_path(self.home / "trajectories.sqlite3")
        config.guard_path(Path("/tmp/x/y.db"))

    def test_una_sesion_completa_no_escribe_en_auto_memory(self):
        fake_home = self.home / "fakehome"
        memory = fake_home / ".claude" / "projects" / "-proj" / "memory"
        memory.mkdir(parents=True)
        (memory / "MEMORY.md").write_text("notas nativas\n", encoding="utf-8")
        before = {p: p.stat().st_mtime_ns for p in memory.rglob("*")}

        saved = os.environ.get("HOME")
        os.environ["HOME"] = str(fake_home)
        try:
            for event, extra in (("SessionStart", {}),
                                 ("UserPromptSubmit", {"user_input": "los tests fallan"}),
                                 ("PostToolUse", {"tool_name": "Read",
                                                  "tool_input": {"file_path": "a.py"},
                                                  "tool_output": "x"}),
                                 ("PostToolUseFailure", {"tool_name": "Bash",
                                                         "tool_input": {"command": "pytest"},
                                                         "error_message": "boom"}),
                                 ("PreCompact", {"compaction_reason": "auto"}),
                                 ("Stop", {}), ("SessionEnd", {})):
                hook.dispatch(event, dict({"session_id": "coex", "cwd": "."}, **extra))
        finally:
            if saved is None:
                os.environ.pop("HOME", None)
            else:
                os.environ["HOME"] = saved

        after = {p: p.stat().st_mtime_ns for p in memory.rglob("*")}
        self.assertEqual(set(before), set(after), "aparecieron o desaparecieron archivos")
        for path, mtime in before.items():
            self.assertEqual(after[path], mtime, "se modificó %s" % path)
        self.assertEqual((memory / "MEMORY.md").read_text(encoding="utf-8"), "notas nativas\n")


if __name__ == "__main__":
    unittest.main()


class SingleStoreTest(unittest.TestCase):
    """Regresión: la ruta del store no puede depender de quién ejecuta el proceso.

    Claude Code le pasa CLAUDE_PLUGIN_DATA a los hooks pero no al Bash tool. Mientras
    influyó en `home()`, los hooks escribían en ~/.claude/plugins/data/<id>/ y
    `nightshift init` configuraba ~/.nightshift: la captura nunca arrancaba y `status`
    decía cero para siempre.
    """

    def setUp(self):
        from nightshift import config
        self.config = config
        self._saved = {k: os.environ.get(k) for k in ("NIGHTSHIFT_HOME", "CLAUDE_PLUGIN_DATA")}
        os.environ.pop("NIGHTSHIFT_HOME", None)
        os.environ.pop("CLAUDE_PLUGIN_DATA", None)

    def tearDown(self):
        for key, value in self._saved.items():
            if value is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = value

    def test_claude_plugin_data_no_mueve_el_store(self):
        sin = self.config.home()
        os.environ["CLAUDE_PLUGIN_DATA"] = "/tmp/otro/lugar/nightshift"
        con = self.config.home()
        self.assertEqual(sin, con,
                         "CLAUDE_PLUGIN_DATA no puede cambiar dónde vive el store")

    def test_default_es_home_del_usuario(self):
        self.assertEqual(self.config.home(), Path.home() / ".nightshift")

    def test_nightshift_home_si_manda(self):
        os.environ["NIGHTSHIFT_HOME"] = "/tmp/elegido"
        self.assertEqual(self.config.home(), Path("/tmp/elegido"))
