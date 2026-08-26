#!/bin/sh
# Experimento 2 — Lo que se descartó no se pierde (capacidad B)
#
# Tres sesiones sobre el mismo problema. En la primera se prueba un camino y el usuario
# lo corrige. En la segunda se resuelve de otra forma. Dream consolida las dos.
#
# Lo que hay que mirar: la trayectoria corregida **sigue estando**, enlazada a la que la
# reemplazó. Auto Dream borra lo contradicho; acá sobrevive con su precondición, y
# `why` la puede reconstruir tres semanas después.
#
# Corre en un store desechable. No toca el store real ni el conteo del gate de M1.
set -eu

RAIZ=$(cd "$(dirname "$0")/.." && pwd)
TRABAJO=$(mktemp -d /tmp/nightshift-exp2-XXXXXX)
export NIGHTSHIFT_HOME="$TRABAJO/store"
NS="$RAIZ/bin/nightshift"

limpiar() { [ "${CONSERVAR:-0}" = "1" ] || rm -rf "$TRABAJO"; }
trap limpiar EXIT

"$NS" init >/dev/null
echo "store del experimento: $NIGHTSHIFT_HOME"
echo

echo "── Sesión 1 · se prueba un camino y el usuario lo corrige ─────────────────────"
python3 - "$RAIZ" <<'PY'
import sys
sys.path.insert(0, sys.argv[1])
from nightshift import hook

base = {"session_id": "exp2-descartada", "cwd": sys.argv[1]}
hook.dispatch("SessionStart", dict(base))
hook.dispatch("UserPromptSubmit", dict(base, prompt="los tests fallan al leer la config y "
                                                    "tarda muchísimo"))
hook.dispatch("PostToolUse", dict(
    base, tool_name="Bash", tool_input={"command": "pytest -q tests/test_config.py"},
    tool_response={"stdout": "2 failed — TimeoutError tras 30s", "stderr": ""}))
hook.dispatch("PostToolUse", dict(
    base, tool_name="Edit", tool_input={"file_path": "servicio/ajustes.py"},
    tool_response={"oldString": "LIMITE = 2000", "newString": "LIMITE = 30000"}))
hook.dispatch("UserPromptSubmit", dict(
    base, prompt="no, eso está mal: subir el timeout tapa el problema, no lo arregla"))
hook.dispatch("Stop", dict(base, last_assistant_message="revierto"))
hook.dispatch("SessionEnd", dict(base, reason="clear"))
print("  probó: subir el límite de tiempo a 30 s")
print("  el usuario la contradijo → la trayectoria cierra como `user_corrected`")
PY
echo

echo "── Sesión 2 · se resuelve de otra forma ──────────────────────────────────────"
python3 - "$RAIZ" <<'PY'
import sys
sys.path.insert(0, sys.argv[1])
from nightshift import hook

base = {"session_id": "exp2-buena", "cwd": sys.argv[1]}
hook.dispatch("SessionStart", dict(base))
hook.dispatch("UserPromptSubmit", dict(base, prompt="los tests de config siguen fallando "
                                                    "por timeout"))
hook.dispatch("PostToolUseFailure", dict(
    base, tool_name="Bash", tool_use_id="t1", is_interrupt=False,
    tool_input={"command": "pytest -q tests/test_config.py"},
    error="TimeoutError: el lector espera una respuesta que nunca llega"))
hook.dispatch("PostToolUse", dict(
    base, tool_name="Read", tool_input={"file_path": "servicio/red.py"},
    tool_response={"type": "text",
                   "file": {"content": "def leer(): return cliente.pedir(timeout=None)"}}))
hook.dispatch("PostToolUse", dict(
    base, tool_name="Edit", tool_input={"file_path": "servicio/red.py"},
    tool_response={"oldString": "timeout=None", "newString": "timeout=LIMITES['consulta']"}))
hook.dispatch("PostToolUse", dict(
    base, tool_name="Bash", tool_input={"command": "pytest -q"},
    tool_response={"stdout": "24 passed en 1.2s", "stderr": ""}))
hook.dispatch("Stop", dict(base, last_assistant_message="listo"))
hook.dispatch("SessionEnd", dict(base, reason="clear"))
print("  encontró que el llamador pasaba timeout=None y lo hizo leer el límite configurado")
print("  la suite pasa → la trayectoria cierra como `tests_passed`")
PY
echo

echo "── Dream consolida las dos ───────────────────────────────────────────────────"
"$NS" dream --lookback-days 3650 2>&1 | grep -E "^  |candidatas|contradicciones|patrón|USD" | head -12
echo

echo "── Lo que quedó en el store ──────────────────────────────────────────────────"
"$NS" status | sed -n '/trayectorias:/,/inyecciones/p'
echo

echo "── El punto del experimento ──────────────────────────────────────────────────"
python3 - "$RAIZ" <<'PY'
import sys
sys.path.insert(0, sys.argv[1])
from nightshift import store

conn = store.connect()
try:
    for fila in conn.execute("SELECT id, status, outcome_result, superseded_by"
                             " FROM trajectories ORDER BY created_at"):
        print("  %s  %-11s %-15s %s" % (
            fila["id"][:8], fila["status"], fila["outcome_result"] or "—",
            ("superseded_by " + fila["superseded_by"][:8]) if fila["superseded_by"] else ""))
    borradas = conn.execute("SELECT COUNT(*) c FROM trajectories").fetchone()["c"]
    print()
    print("  trayectorias en el store: %d. La contradicha NO se borró." % borradas)
finally:
    conn.close()
PY
echo
echo '── why reconstruye la alternativa descartada ─────────────────────────────────'
VIEJA=$(python3 - "$RAIZ" <<'PY'
import sys
sys.path.insert(0, sys.argv[1])
from nightshift import store
conn = store.connect()
try:
    fila = conn.execute("SELECT id FROM trajectories WHERE status='superseded'").fetchone()
    print(fila["id"] if fila else "")
finally:
    conn.close()
PY
)
if [ -n "$VIEJA" ]; then
  "$NS" why "$VIEJA" | sed -n '1,9p;/contradicha por/,+2p'
else
  echo "  (dream no enlazó una contradicción en esta corrida — ver la salida de arriba)"
fi
echo
echo "Store conservado en: $NIGHTSHIFT_HOME  (CONSERVAR=1 para no borrarlo)"
