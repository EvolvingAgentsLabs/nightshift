"""El experimento que le pregunta a una persona por lo que dream proyectó.

Vive en `experimentos/`, no en `nightshift/`: no toca el flujo por defecto, no participa
del brazo S1 del benchmark y no cierra ningún gate. Pero tiene tests, y son sobre las dos
promesas que lo hacen honesto — las dos son fáciles de romper sin querer:

1. **No escribe en el store.** Lo abre en modo sólo lectura de SQLite, así que la promesa
   no depende de la disciplina de quien lo edite después.
2. **No promueve nada.** Una respuesta humana no es una reproducción contra un gate
   (ADR-002), así que ninguna trayectoria puede cambiar de estado por esta vía.
"""

import importlib.util
import json
import sqlite3
import unittest
from pathlib import Path

from tests.base import IsolatedStoreTest
from nightshift import config, store

RAIZ = Path(__file__).resolve().parent.parent


def _cargar():
    """El experimento no es un paquete: se carga por ruta, como lo corre una persona."""
    ruta = RAIZ / "experimentos" / "preguntar.py"
    spec = importlib.util.spec_from_file_location("preguntar", ruta)
    modulo = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(modulo)
    return modulo


class PreguntarTest(IsolatedStoreTest):
    def sembrar_candidata_con_proyecciones(self, proyectadas):
        conn = store.connect()
        try:
            tid = store.open_trajectory(conn, session_id="s", repo_fingerprint="f" * 64,
                                        task_type="debug_test_failure", base_commit="abc1234",
                                        redaction={"redactor_version": "0.1.0"})
            store.append_step(conn, tid, kind="tool_failure", tool="run_shell",
                              error_message="algo falló", decisive=True)
            store.close_trajectory(conn, tid, result="tests_passed")
            store.promote_to_candidate(
                conn, tid,
                abstraction={"pattern": "un patrón cualquiera", "signals": ["se vio esto"],
                             "decisive_signal": None},
                valid_when=[{"condition": "una condición", "source": "inferred"}],
                projected_signals=proyectadas)
            return tid
        finally:
            conn.close()

    def test_lista_lo_proyectado_y_no_lo_observado(self):
        """La frontera de ADR-004: se pregunta por conjeturas, no por observaciones."""
        preguntar = _cargar()
        tid = self.sembrar_candidata_con_proyecciones(
            ["esto lo anticipó el modelo", "y esto también"])
        conn = sqlite3.connect(str(config.db_path()))
        conn.row_factory = sqlite3.Row
        try:
            items = preguntar.proyecciones(conn)
        finally:
            conn.close()
        self.assertEqual(len(items), 2)
        self.assertEqual({i["projected"] for i in items},
                         {"esto lo anticipó el modelo", "y esto también"})
        self.assertTrue(all(i["trajectory"] == tid for i in items))
        for item in items:
            self.assertNotIn("se vio esto", item["projected"],
                             "una señal observada no es algo que preguntar")

    def test_sin_proyecciones_no_hay_nada_que_preguntar(self):
        preguntar = _cargar()
        self.sembrar_candidata_con_proyecciones([])
        conn = sqlite3.connect(str(config.db_path()))
        conn.row_factory = sqlite3.Row
        try:
            self.assertEqual(preguntar.proyecciones(conn), [])
        finally:
            conn.close()

    def test_el_store_se_abre_en_solo_lectura(self):
        """Que la promesa la sostenga SQLite y no mi disciplina."""
        preguntar = _cargar()
        self.sembrar_candidata_con_proyecciones(["una conjetura"])
        conn = preguntar.abrir_solo_lectura(config.db_path())
        try:
            with self.assertRaises(sqlite3.OperationalError):
                conn.execute("UPDATE trajectories SET status = 'procedure'")
        finally:
            conn.close()

    def test_el_veredicto_no_cambia_el_estado_de_nada(self):
        """Una respuesta humana no es una reproducción contra un gate (ADR-002)."""
        preguntar = _cargar()
        tid = self.sembrar_candidata_con_proyecciones(["una conjetura"])
        salida = Path(self.tmp.name) / "veredictos.jsonl" \
            if hasattr(self, "tmp") else Path(config.db_path()).parent / "veredictos.jsonl"
        preguntar.main(["--store", str(config.db_path().parent),
                        "--salida", str(salida), "--dry-run"])
        conn = store.connect()
        try:
            self.assertEqual(store.get_trajectory(conn, tid)["status"], "candidate")
        finally:
            conn.close()
        self.assertFalse(salida.exists(), "--dry-run no escribe veredictos")

    def test_las_opciones_distinguen_no_la_vi_de_no_puede_pasar(self):
        """Son respuestas distintas, y confundirlas pierde la información cara."""
        preguntar = _cargar()
        etiquetas = [etiqueta for etiqueta, _, _ in preguntar.OPCIONES]
        self.assertIn("la vi", etiquetas)
        self.assertIn("no puede pasar", etiquetas)
        self.assertIn("no la vi todavía", etiquetas)
        self.assertIn("no sé", etiquetas)


if __name__ == "__main__":
    unittest.main()
