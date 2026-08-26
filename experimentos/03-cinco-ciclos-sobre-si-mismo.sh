#!/bin/sh
# Experimento 3 — Cinco ciclos del plugin sobre sus propios problemas
#
# Cinco sesiones reales de Claude Code sobre una copia de este repositorio, con el plugin
# cargado y capturando. Entre ciclo y ciclo corre dream. Cada ciclo ataca un problema
# abierto distinto de `LATER.md`, y cada uno arranca con lo que los anteriores dejaron.
#
# Qué mirar: si lo que se inyecta en el ciclo N sirvió para el ciclo N+1, y qué tan bien
# abstrae dream cuando el grupo crece de una trayectoria a cuatro.
#
# Corre sobre una copia del repo y un store propio. **No toca tu repo ni tu store**, y
# por lo tanto no suma al conteo del gate de M1: son sesiones dirigidas por un script,
# no por una persona trabajando.
set -eu

RAIZ=$(cd "$(dirname "$0")/.." && pwd)
MODELO="${MODELO:-sonnet}"
TRABAJO="${TRABAJO:-$(mktemp -d /tmp/nightshift-ciclos-XXXXXX)}"
COPIA="$TRABAJO/repo"
export NIGHTSHIFT_HOME="$TRABAJO/store"
NS="$RAIZ/bin/nightshift"

git -C "$RAIZ" worktree list >/dev/null 2>&1 || true
rm -rf "$COPIA"
git clone -q "$RAIZ" "$COPIA"
"$NS" init >/dev/null

echo "cinco ciclos sobre una copia del repo"
echo "  copia : $COPIA"
echo "  store : $NIGHTSHIFT_HOME"
echo "  modelo: $MODELO"
echo

ciclo() {
  n="$1"; titulo="$2"; pedido="$3"
  echo "══ Ciclo $n · $titulo ═══════════════════════════════════════════════════════"

  inyectado=$(python3 -c "
import sys; sys.path.insert(0, '$RAIZ')
from nightshift import store
conn = store.connect()
try:
    print(conn.execute('SELECT COUNT(*) c FROM injections').fetchone()['c'])
finally:
    conn.close()")

  salida=$(cd "$COPIA" && claude -p "$pedido" --model "$MODELO" \
    --output-format stream-json --verbose --plugin-dir "$RAIZ" \
    --permission-mode bypassPermissions --allow-dangerously-skip-permissions \
    2>/dev/null || true)

  calls=$(printf '%s' "$salida" | python3 -c "
import json, sys
n = 0
for l in sys.stdin:
    l = l.strip()
    if not l.startswith('{'): continue
    try: d = json.loads(l)
    except ValueError: continue
    if d.get('type') == 'assistant':
        n += sum(1 for b in d.get('message', {}).get('content') or []
                 if b.get('type') == 'tool_use')
print(n)")

  # ¿pasa el gate del repo después de este ciclo?
  gate=$(cd "$COPIA" && make check >/dev/null 2>&1 && echo OK || echo FALLA)
  cambios=$(cd "$COPIA" && git status --porcelain | wc -l | tr -d ' ')

  nuevas=$(python3 -c "
import sys; sys.path.insert(0, '$RAIZ')
from nightshift import store
conn = store.connect()
try:
    print(conn.execute('SELECT COUNT(*) c FROM injections').fetchone()['c'] - $inyectado)
finally:
    conn.close()")

  printf '  tool_calls=%-4s archivos tocados=%-4s make check=%-6s inyecciones recibidas=%s\n' \
    "$calls" "$cambios" "$gate" "$nuevas"
  echo "$n,$titulo,$calls,$cambios,$gate,$nuevas" >> "$TRABAJO/ciclos.csv"

  # El ciclo cierra su sesión y dream consolida antes del siguiente.
  echo "  dream:"
  "$NS" dream --lookback-days 3650 2>/dev/null \
    | grep -E "^  [0-9a-f]{8}|candidatas:|sin patrón" | head -3 | sed 's/^/    /'
  echo
}

ciclo 1 "medir el store" \
  "En este repo, \`nightshift status\` no dice cuánto ocupa el store en disco, y la política de retención está diferida en LATER.md justamente porque no hay con qué medir. Agregá el tamaño del store al reporte de \`status\`, con un test que falle si se revierte. Corré 'make check' al final."

ciclo 2 "próxima corrida" \
  "En este repo, \`nightshift schedule status\` muestra las últimas corridas pero no dice cuándo es la próxima, y eso está anotado como pendiente en LATER.md. Agregalo para el backend launchd, con un test. Corré 'make check' al final."

ciclo 3 "tope de grupos en dream" \
  "En este repo, \`nightshift dream\` consolida todos los grupos del período y desde ADR-003 cada grupo cuesta dinero. Agregá una opción para limitar cuántos grupos consolida una corrida, con su test. Corré 'make check' al final."

ciclo 4 "trazabilidad del costo" \
  "En este repo, \`nightshift why\` muestra la abstracción de una candidate pero no dice cuánto costó consolidarla ni con qué modelo, y la auditabilidad es la condición de éxito 3 de la spec. Hacé que esa información quede registrada y se muestre, con un test. Corré 'make check' al final."

ciclo 5 "celdas que no terminaron" \
  "En este repo, el reporte de \`nightshift bench report\` no distingue una celda que falló de una que no llegó a terminar por timeout, y eso cambia cómo se lee un resultado. Arreglalo con un test. Corré 'make check' al final."

echo "══ Resumen ═════════════════════════════════════════════════════════════════"
(echo "ciclo,problema,tool_calls,archivos,make_check,inyecciones"; cat "$TRABAJO/ciclos.csv") \
  | column -s, -t 2>/dev/null || cat "$TRABAJO/ciclos.csv"
echo
"$NS" status | sed -n '/trayectorias:/,/^$/p'
echo "diff completo: git -C $COPIA diff"
