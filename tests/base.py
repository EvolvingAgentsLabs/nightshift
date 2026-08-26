"""Base para los tests: cada caso corre contra un NIGHTSHIFT_HOME desechable.

Ningún test puede tocar el store real del usuario ni su HOME.
"""

from __future__ import annotations

import os
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))


class IsolatedStoreTest(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory(prefix="nightshift-test-")
        self.home = Path(self._tmp.name)
        self._saved = {k: os.environ.get(k) for k in ("NIGHTSHIFT_HOME", "CLAUDE_PLUGIN_DATA")}
        os.environ["NIGHTSHIFT_HOME"] = str(self.home)
        os.environ.pop("CLAUDE_PLUGIN_DATA", None)
        from nightshift import config
        config.init(force=True)

    def tearDown(self):
        for key, value in self._saved.items():
            if value is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = value
        self._tmp.cleanup()
