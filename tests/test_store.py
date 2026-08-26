"""El store persiste y exporta en el formato que M0 congeló."""

import unittest

from tests.base import IsolatedStoreTest
from nightshift import store


class StoreTest(IsolatedStoreTest):
    def test_ciclo_de_vida(self):
        conn = store.connect()
        try:
            tid = store.open_trajectory(conn, session_id="s1", repo_fingerprint="a" * 64,
                                        task_type="debug_test_failure", base_commit="abc1234",
                                        redaction={"redactor_version": "0.1.0"})
            self.assertEqual(store.active_trajectory(conn, "s1")["id"], tid)

            store.append_step(conn, tid, kind="tool_use", tool="run_shell", tool_native="Bash",
                              result_summary="3 tests fallan")
            store.append_step(conn, tid, kind="tool_failure", tool="run_shell",
                              error_message="UnicodeDecodeError", decisive=True)
            self.assertEqual(len(store.steps_of(conn, tid)), 2)

            self.assertEqual(store.mark_last_contradicted(conn, tid), 1)
            self.assertTrue(store.steps_of(conn, tid)[1]["contradicted"])

            status = store.close_trajectory(conn, tid, result="tests_passed", gate_id="make-check")
            self.assertEqual(status, "closed")
            self.assertIsNone(store.active_trajectory(conn, "s1"))
        finally:
            conn.close()

    def test_abandoned_va_a_discarded(self):
        conn = store.connect()
        try:
            tid = store.open_trajectory(conn, session_id="s2", repo_fingerprint="b" * 64,
                                        task_type="general")
            self.assertEqual(store.close_trajectory(conn, tid, result="abandoned"), "discarded")
        finally:
            conn.close()

    def test_max_steps_frena(self):
        conn = store.connect()
        try:
            tid = store.open_trajectory(conn, session_id="s3", repo_fingerprint="c" * 64,
                                        task_type="general")
            for _ in range(5):
                store.append_step(conn, tid, kind="tool_use", max_steps=3)
            self.assertEqual(len(store.steps_of(conn, tid)), 3)
        finally:
            conn.close()

    def test_export_tiene_la_forma_del_schema(self):
        conn = store.connect()
        try:
            tid = store.open_trajectory(conn, session_id="s4", repo_fingerprint="d" * 64,
                                        task_type="general", base_commit="abc1234",
                                        redaction={"redactor_version": "0.1.0"})
            store.append_step(conn, tid, kind="tool_use", tool="read_file")
            store.close_trajectory(conn, tid, result="unknown")
            doc = store.export_trajectory(conn, tid)
            self.assertEqual(doc["schema_version"], "trajectory.v1")
            for field in ("id", "created_at", "status", "harness", "repo_fingerprint",
                          "task_type", "steps", "redaction"):
                self.assertIn(field, doc)
            self.assertEqual(doc["steps"][0]["index"], 0)
        finally:
            conn.close()

    def test_prefijo_de_id_resuelve(self):
        conn = store.connect()
        try:
            tid = store.open_trajectory(conn, session_id="s5", repo_fingerprint="e" * 64,
                                        task_type="general")
            self.assertEqual(store.get_trajectory(conn, tid[:8])["id"], tid)
        finally:
            conn.close()


if __name__ == "__main__":
    unittest.main()
