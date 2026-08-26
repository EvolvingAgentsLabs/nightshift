"""`nightshift status` reporta el tamaño del store en disco.

No hay política de retención todavía (LATER.md, "Retención y tamaño del store") porque
no había con qué medir cuánto ocupa. Este test es la medición: si `status` deja de
reportar el tamaño, o el tamaño reportado no refleja lo que hay en disco, falla acá.
"""

import contextlib
import io
import unittest

from tests.base import IsolatedStoreTest
from nightshift import cli, store


class StatusSizeTest(IsolatedStoreTest):
    def test_status_reporta_el_tamano_del_store(self):
        conn = store.connect()
        try:
            tid = store.open_trajectory(conn, session_id="s1", repo_fingerprint="a" * 64,
                                        task_type="general")
            store.append_step(conn, tid, kind="tool_use", tool="read_file")
        finally:
            conn.close()

        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            code = cli.main(["status"])
        self.assertEqual(code, 0)

        primera_linea = out.getvalue().splitlines()[1]
        self.assertTrue(primera_linea.startswith("store: "))
        self.assertRegex(primera_linea, r"\((\d+(\.\d+)? (B|KB|MB|GB)) en disco\)")

    def test_status_refleja_el_crecimiento_del_store(self):
        antes = store.store_size_bytes()

        conn = store.connect()
        try:
            tid = store.open_trajectory(conn, session_id="s2", repo_fingerprint="b" * 64,
                                        task_type="general")
            for _ in range(200):
                store.append_step(conn, tid, kind="tool_use", tool="read_file",
                                  result_summary="x" * 500)
        finally:
            conn.close()

        despues = store.store_size_bytes()
        self.assertGreater(despues, antes)

        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            cli.main(["status"])
        primera_linea = out.getvalue().splitlines()[1]
        self.assertNotIn("(0 B en disco)", primera_linea)


if __name__ == "__main__":
    unittest.main()
