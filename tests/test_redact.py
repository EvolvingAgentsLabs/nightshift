"""El redactor es determinista y no deja pasar secretos. Gate de M1."""

import unittest

from tests.base import IsolatedStoreTest  # noqa: F401  (fija sys.path)
from nightshift.redact import Redactor


class RedactorTest(unittest.TestCase):
    def redactor(self):
        return Redactor(identifiers=["histora", "EvolvingAgentsLabs"],
                        deny_paths=["**/.env", "**/.ssh/**", "**/*.pem"],
                        home_dir="/home/matias")

    def test_determinista(self):
        text = 'API_TOKEN="tok_live_abc123456" en /home/matias/histora/src/a.py'
        first = self.redactor().text(text)
        second = self.redactor().text(text)
        self.assertEqual(first, second)

    def test_secretos_no_sobreviven(self):
        cases = [
            ("sk-ant-api03-abcdefghijklmnopqrstuvwxyz", "sk-ant-api03-abcdefghijklmnopqrstuvwxyz"),
            ("ghp_abcdefghijklmnopqrstuvwxyz0123", "ghp_abcdefghijklmnopqrstuvwxyz0123"),
            ("AKIAIOSFODNN7EXAMPLE", "AKIAIOSFODNN7EXAMPLE"),
            ('PASSWORD="hunter2hunter2"', "hunter2hunter2"),
            ("https://user:sup3rs3cret@github.com/x/y.git", "sup3rs3cret"),
        ]
        red = self.redactor()
        for raw, secret in cases:
            with self.subTest(raw=raw):
                self.assertNotIn(secret, red.text(raw))

    def test_identificadores_del_repo(self):
        out = self.redactor().text("el bug esta en histora, repo de EvolvingAgentsLabs")
        self.assertNotIn("histora", out.lower())
        self.assertNotIn("evolvingagentslabs", out.lower())

    def test_home_y_rutas_absolutas(self):
        out = self.redactor().text("abri /home/matias/proyectos/x/src/main.py")
        self.assertNotIn("/home/matias", out)
        self.assertNotIn("proyectos", out)

    def test_deny_paths(self):
        red = self.redactor()
        for denied in ("/home/matias/p/.env", "/home/matias/.ssh/id_rsa", "/x/cert.pem"):
            self.assertTrue(red.is_denied(denied), denied)
        for allowed in ("/home/matias/p/README.md", "/x/src/main.py"):
            self.assertFalse(red.is_denied(allowed), allowed)

    def test_obj_descarta_denegados_y_cuenta(self):
        red = self.redactor()
        out = red.obj({"file_path": "/home/matias/p/.env", "command": "cat x", "n": 3})
        self.assertNotIn("file_path", out)
        self.assertEqual(out["n"], 3)
        self.assertEqual(red.deny_path_hits, 1)

    def test_report_estable(self):
        red = self.redactor()
        red.text("token ghp_abcdefghijklmnopqrstuvwxyz0123")
        report = red.report()
        self.assertIn("redactor_version", report)
        self.assertIn("secret.github", report["rules_applied"])
        self.assertEqual(report["rules_applied"], sorted(report["rules_applied"]))


if __name__ == "__main__":
    unittest.main()


class SecretKeyNameTest(unittest.TestCase):
    """Regresión: el selftest encontró que un secreto bajo una clave de diccionario
    escapaba a `secret.assignment`, que espera CLAVE=valor dentro de un mismo string."""

    def redactor(self):
        return Redactor(identifiers=[], deny_paths=[], home_dir="/home/x")

    def test_valor_bajo_clave_secreta_se_redacta(self):
        red = self.redactor()
        out = red.obj({"command": "deploy", "env": {"API_TOKEN": "tok_live_999",
                                                    "AWS_SECRET_ACCESS_KEY": "abc/def+ghi"}})
        self.assertEqual(out["env"]["API_TOKEN"], "<SECRET>")
        self.assertEqual(out["env"]["AWS_SECRET_ACCESS_KEY"], "<SECRET>")
        self.assertEqual(out["command"], "deploy")
        self.assertIn("secret.key_name", red.report()["rules_applied"])

    def test_claves_inocentes_no_se_tocan(self):
        red = self.redactor()
        out = red.obj({"file_path": "a.py", "limit": 10, "keyword": "parser"})
        self.assertEqual(out["limit"], 10)
        self.assertEqual(out["keyword"], "parser")
