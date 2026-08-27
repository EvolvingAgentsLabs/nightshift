"""El contraste entre una alternativa descartada y la que la reemplazó (ADR-005).

`mark_superseded` guardaba el enlace y nada más: *que* una trayectoria reemplazó a otra,
nunca **qué cambió, qué compró el cambio, y cuándo la vieja seguía teniendo razón**. La
spec §4.2 promete que "una alternativa descartada con su precondición es conocimiento y
sin ella es ruido" — y la precondición no la calculaba nadie. Sin ella, no borrar lo
contradicho guarda un cadáver en vez de una lección.

Lo que se prueba acá es esa frontera y las dos formas de arruinarla:

- un contraste que falla **no puede** llevarse puesta la supersesión: el enlace vale por
  sí solo, y perderlo sería borrar lo contradicho, que es justo lo que ADR-001 dice que
  no hacemos;
- y el contraste tiene que llegar a quien recibe la ganadora, o dentro de tres semanas
  alguien propone el camino descartado y lo recorre entero.
"""

import json
import unittest

from tests.base import IsolatedStoreTest
from nightshift import config, dream, redact, retrieve, store

FP = "f" * 64


def _redactor():
    return redact.Redactor(identifiers=[], deny_paths=config.DEFAULT_DENY_PATHS,
                           home_dir=None)


def _sembrar(conn, *, result="tests_passed"):
    tid = store.open_trajectory(conn, session_id="s", repo_fingerprint=FP,
                               task_type="debug_test_failure", base_commit="abc1234",
                               redaction={"redactor_version": "0.1.0"})
    store.append_step(conn, tid, kind="tool_failure", tool="run_shell",
                      error_message="timeout a los 2000 ms", decisive=True)
    store.close_trajectory(conn, tid, result=result)
    return tid


class ValidacionTest(IsolatedStoreTest):
    def test_sin_changed_no_hay_contraste(self):
        """Un contraste que no dice qué cambió no dice nada."""
        contraste, problemas = dream.validate_contrast(
            {"bought": "deja de ser posible que el gate mida cero"},
            redactor=_redactor(), home_dir=None)
        self.assertIsNone(contraste)
        self.assertTrue(problemas)

    def test_una_ruta_en_el_contraste_lo_rechaza(self):
        _, problemas = dream.validate_contrast(
            {"changed": "se cambio el orden en el modulo /Users/alguien/proyecto/src"},
            redactor=_redactor(), home_dir=None)
        self.assertTrue(problemas)

    def test_la_precondicion_de_la_descartada_se_conserva(self):
        contraste, problemas = dream.validate_contrast({
            "changed": "La matriz pasa a iterar por repeticion antes que por fila.",
            "bought": "Cortar por tiempo deja de dejar los brazos con distinto n.",
            "old_valid_when": ["cuando la corrida siempre termina entera"],
            "cost": None,
        }, redactor=_redactor(), home_dir=None)
        self.assertEqual(problemas, [])
        self.assertEqual(contraste["old_valid_when"],
                         ["cuando la corrida siempre termina entera"])
        self.assertNotIn("cost", contraste, "un costo nulo no se guarda como texto")


class SupersesionTest(IsolatedStoreTest):
    def test_el_enlace_sobrevive_aunque_el_contraste_falle(self):
        """El contraste es un extra. Perder la supersesión sería borrar lo contradicho.

        Que es exactamente lo que ADR-001 dice que nightshift no hace y Auto Dream sí.
        """
        conn = store.connect()
        vieja, nueva = _sembrar(conn, result="user_corrected"), _sembrar(conn)
        store.mark_superseded(conn, vieja, nueva, contrast=None)
        fila = store.get_trajectory(conn, vieja)
        conn.close()
        self.assertEqual(fila["status"], "superseded")
        self.assertEqual(fila["superseded_by"], nueva)
        self.assertIsNone(fila["contrast_json"])

    def test_el_contraste_llega_a_quien_recibe_la_ganadora(self):
        """Sin esto, el camino descartado se vuelve a proponer y se recorre entero."""
        conn = store.connect()
        vieja, nueva = _sembrar(conn, result="user_corrected"), _sembrar(conn)
        store.promote_to_candidate(
            conn, nueva,
            abstraction={"pattern": "El llamador pasaba el limite sin resolver y la capa "
                                    "de abajo lo tomaba como ausente."},
            valid_when=[], hypothesis=None, weight=0.6)
        store.mark_superseded(conn, vieja, nueva, contrast={
            "changed": "En vez de subir el limite de tiempo, se arregla quien lo pasa.",
            "bought": "Deja de ser posible que el sintoma se tape sin tocar la causa.",
            "old_valid_when": ["cuando el limite es efectivamente demasiado bajo para el "
                               "trabajo real"],
        })
        scored = retrieve.candidates(conn, task_type="debug_test_failure",
                                     repo_fingerprint=FP, cfg=config.load())
        texto, chosen = retrieve.render(conn, scored, max_injected=3, native_memory=False,
                                        task_type="debug_test_failure",
                                        repo_fingerprint=FP)
        conn.close()
        self.assertTrue(chosen)
        self.assertIn("reemplazó a", texto)
        self.assertIn("qué cambió", texto)
        self.assertIn("la descartada seguía siendo la correcta cuando", texto)
        # Y la descartada no se inyecta como si fuera una opción vigente.
        self.assertNotIn(vieja[:8] + "` — debug_test_failure · trayectoria cruda", texto)

    def test_una_supersesion_sin_contraste_lo_dice(self):
        """Callarlo haría creer que no había nada que contrastar."""
        conn = store.connect()
        vieja, nueva = _sembrar(conn, result="user_corrected"), _sembrar(conn)
        store.promote_to_candidate(
            conn, nueva, abstraction={"pattern": "Un patron cualquiera que sirve de prueba."},
            valid_when=[], hypothesis=None, weight=0.6)
        store.mark_superseded(conn, vieja, nueva)
        scored = retrieve.candidates(conn, task_type="debug_test_failure",
                                     repo_fingerprint=FP, cfg=config.load())
        texto, _ = retrieve.render(conn, scored, max_injected=3, native_memory=False,
                                   task_type="debug_test_failure", repo_fingerprint=FP)
        conn.close()
        self.assertIn("sin contraste consolidado", texto)


if __name__ == "__main__":
    unittest.main()
