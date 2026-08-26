"""Captura -> export -> validar contra el esquema que M0 congeló.

Es la prueba más barata de que la implementación y la spec no se separaron. Si este
test falla, o el código dejó de respetar `schema/trajectory.v1.json`, o el esquema
cambió sin actualizar el código; en cualquier caso es un bug, no un detalle.
"""

import json
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

from tests.base import IsolatedStoreTest
from nightshift import hook, store

ROOT = Path(__file__).resolve().parent.parent
SCHEMA = ROOT / "schema" / "trajectory.v1.json"


def validator():
    if shutil.which("check-jsonschema"):
        return ["check-jsonschema"]
    if shutil.which("uvx"):
        return ["uvx", "--quiet", "check-jsonschema@0.33.0"]
    return None


class SchemaRoundTripTest(IsolatedStoreTest):
    def capture_one(self):
        base = {"session_id": "rt", "cwd": str(ROOT)}
        hook.dispatch("SessionStart", dict(base))
        hook.dispatch("UserPromptSubmit", dict(base, user_input="los tests fallan"))
        hook.dispatch("PostToolUse", dict(base, tool_name="Read", tool_use_id="a",
                                          tool_input={"file_path": "x.py"}, tool_output="def f()"))
        hook.dispatch("PostToolUseFailure", dict(base, tool_name="Bash", tool_use_id="b",
                                                 tool_input={"command": "pytest -q"},
                                                 error_message="AssertionError"))
        hook.dispatch("PreCompact", dict(base, compaction_reason="manual"))
        hook.dispatch("Stop", dict(base))
        hook.dispatch("SessionEnd", dict(base))
        conn = store.connect()
        try:
            row = conn.execute("SELECT id FROM trajectories").fetchone()
            return store.export_trajectory(conn, row["id"])
        finally:
            conn.close()

    def test_la_trayectoria_capturada_valida(self):
        cmd = validator()
        if cmd is None:
            self.skipTest("check-jsonschema no disponible")
        doc = self.capture_one()
        with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False,
                                         encoding="utf-8") as handle:
            json.dump(doc, handle, ensure_ascii=False)
            path = handle.name
        try:
            result = subprocess.run(cmd + ["--schemafile", str(SCHEMA), path],
                                    capture_output=True, text=True, timeout=300)
            self.assertEqual(result.returncode, 0,
                             "la trayectoria capturada no valida:\n%s%s"
                             % (result.stdout, result.stderr))
        finally:
            Path(path).unlink(missing_ok=True)

    def test_campos_normativos_presentes(self):
        """Chequeo estructural que corre aunque no haya validador instalado."""
        doc = self.capture_one()
        self.assertEqual(doc["schema_version"], "trajectory.v1")
        self.assertRegex(doc["repo_fingerprint"], r"^[a-f0-9]{64}$")
        self.assertIn(doc["status"], ("open", "closed", "candidate", "procedure",
                                      "superseded", "discarded"))
        self.assertIsNone(doc["verified"], "nada puede estar verificado sin dream fase 2")
        self.assertIn("redactor_version", doc["redaction"])
        kinds = {s["kind"] for s in doc["steps"]}
        self.assertIn("tool_failure", kinds)
        self.assertIn("compact_snapshot", kinds)
        for step in doc["steps"]:
            self.assertIn(step["tool"], ("read_file", "edit_file", "write_file", "run_shell",
                                         "search", "fetch", "other", None))


if __name__ == "__main__":
    unittest.main()
