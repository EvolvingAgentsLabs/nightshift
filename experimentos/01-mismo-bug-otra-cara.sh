#!/bin/sh
# Experimento 1 — El mismo bug con otra cara (capacidad A)
#
# Dos tareas del repo fixture de la familia A. Comparten causa —una función que decide
# qué significa "la misma clave" y no saca los caracteres invisibles— y no comparten
# síntoma: la primera revienta con KeyError, la segunda cierra mal los totales.
#
# Se corren tres filas, y la tercera es la que importa:
#   sin-memoria     — dos sesiones independientes, cada una empieza de cero
#   memoria-cruda   — la segunda recibe la **traza** de la primera, sin consolidar
#   memoria-soñada  — dream corre entre las dos, y la segunda recibe el **patrón**
#
# La fila del medio existe porque es la trampa: inyectar la traza cruda es gastar
# contexto en los pasos de otro problema. La tesis del proyecto es que lo que transfiere
# es la abstracción, no el rastro, y ésta es la forma de verlo en vez de afirmarlo.
#
# Cuesta llamadas reales al agente (6 sesiones) más una consolidación. Corre en copias
# desechables del repo fixture y en stores desechables: no toca nada tuyo.
set -eu

RAIZ=$(cd "$(dirname "$0")/.." && pwd)
FIXTURE="$RAIZ/bench/fixtures/familia-a"
MODELO="${MODELO:-sonnet}"
TAREA_A="${TAREA_A:-test_01_indice}"      # síntoma: KeyError con una clave que está
TAREA_B="${TAREA_B:-test_09_reporte}"     # síntoma: los totales no cierran
TRABAJO=$(mktemp -d /tmp/nightshift-exp1-XXXXXX)
NS="$RAIZ/bin/nightshift"

limpiar() { [ "${CONSERVAR:-0}" = "1" ] || rm -rf "$TRABAJO"; }
trap limpiar EXIT

prompt_de() {
  python3 -c "
import json, sys
d = json.load(open('$FIXTURE/fixture.json'))
print(next(t['prompt'] for t in d['tasks'] if t['id'] == '$1'))"
}

# Una sesión: copia limpia del repo, el agente trabaja, el gate dice si resolvió.
correr() {
  fila="$1"; tarea="$2"; repo="$TRABAJO/$fila-$tarea"
  cp -R "$FIXTURE" "$repo"
  rm -rf "$repo/.referencia" "$repo/__pycache__" "$repo/tests/__pycache__"
  ( cd "$repo" && git init -q -b main \
      && git remote add origin https://example.invalid/registro-fixture.git \
      && git add -A && git -c user.email=x@y.z -c user.name=x commit -qm fixture )

  # `&& echo 0 || echo 1` y no `; echo $?`: con `set -e` el subshell muere cuando el gate
  # falla, y el gate **tiene** que fallar antes de que el agente trabaje.
  antes=$(cd "$repo" && NIGHTSHIFT_BENCH_TASK="$tarea" sh gate.sh >/dev/null 2>&1 \
            && echo 0 || echo 1)

  extra=""
  [ "$fila" != "sin-memoria" ] && extra="--plugin-dir $RAIZ"
  # shellcheck disable=SC2086
  salida=$(cd "$repo" && NIGHTSHIFT_HOME="$STORE" claude -p "$(prompt_de "$tarea")" \
    --model "$MODELO" --output-format stream-json --verbose \
    --permission-mode bypassPermissions $extra \
    2>/dev/null || true)

  despues=$(cd "$repo" && NIGHTSHIFT_BENCH_TASK="$tarea" sh gate.sh >/dev/null 2>&1 \
              && echo 0 || echo 1)

  calls=$(printf '%s' "$salida" | python3 -c "
import json, sys
n = 0
for linea in sys.stdin:
    linea = linea.strip()
    if not linea.startswith('{'):
        continue
    try:
        d = json.loads(linea)
    except ValueError:
        continue
    if d.get('type') == 'assistant':
        n += sum(1 for b in d.get('message', {}).get('content') or []
                 if b.get('type') == 'tool_use')
print(n)")

  resuelto=no
  [ "$antes" != "0" ] && [ "$despues" = "0" ] && resuelto=sí
  printf '  %-15s %-16s gate %s→%s  resuelto=%-3s tool_calls=%s\n' \
    "$fila" "$tarea" "$antes" "$despues" "$resuelto" "$calls"
  echo "$fila,$tarea,$resuelto,$calls" >> "$TRABAJO/resultados.csv"
}

# Qué recibió la segunda sesión de una fila: la traza cruda o el patrón consolidado.
inyecciones_de() {
  NIGHTSHIFT_HOME="$TRABAJO/store-$1" python3 -c "
import json, sys
sys.path.insert(0, '$RAIZ')
from nightshift import store

conn = store.connect()
try:
    filas = list(conn.execute(
        'SELECT i.source_trajectory AS src, i.score, i.reason, t.status,'
        ' t.abstraction_json AS abs FROM injections i'
        ' LEFT JOIN trajectories t ON t.id = i.source_trajectory ORDER BY i.at'))
    if not filas:
        print('    ninguna inyección')
    for f in filas:
        print('    ← %s [%s] score=%.2f %s' % (f['src'][:8], f['status'], f['score'],
                                               f['reason']))
        if f['abs']:
            print('      patrón: %s…' % (json.loads(f['abs']).get('pattern') or '')[:86])
        else:
            n = conn.execute('SELECT COUNT(*) c FROM steps WHERE trajectory_id=?',
                             (f['src'],)).fetchone()['c']
            print('      sin patrón: se le pasan %d pasos crudos' % n)
finally:
    conn.close()"
}

echo "Experimento 1 — el mismo bug con otra cara"
echo "modelo: $MODELO · aprende con $TAREA_A · mide con $TAREA_B"
echo

echo "── Fila SIN MEMORIA ──────────────────────────────────────────────────────────"
STORE="$TRABAJO/store-sin"; export STORE
correr sin-memoria "$TAREA_A"
correr sin-memoria "$TAREA_B"
echo

echo "── Fila MEMORIA CRUDA (sin dream) ────────────────────────────────────────────"
STORE="$TRABAJO/store-cruda"; export STORE
NIGHTSHIFT_HOME="$STORE" "$NS" init >/dev/null
correr memoria-cruda "$TAREA_A"
echo "  … la primera quedó capturada; la segunda va a recibir sus pasos sin consolidar"
correr memoria-cruda "$TAREA_B"
echo

echo "── Fila MEMORIA SOÑADA (dream entre las dos) ─────────────────────────────────"
STORE="$TRABAJO/store-sonada"; export STORE
NIGHTSHIFT_HOME="$STORE" "$NS" init >/dev/null
correr memoria-sonada "$TAREA_A"
echo "  … dream consolida antes de la segunda sesión:"
NIGHTSHIFT_HOME="$STORE" "$NS" dream --lookback-days 3650 2>/dev/null \
  | grep -E "^  [0-9a-f]{8}|^      " | head -3 | sed 's/^/  /'
correr memoria-sonada "$TAREA_B"
echo

echo "── Qué recibió la segunda sesión de cada fila ────────────────────────────────"
echo "  memoria-cruda:"
inyecciones_de cruda
echo "  memoria-soñada:"
inyecciones_de sonada
echo

echo "── Resultado ─────────────────────────────────────────────────────────────────"
(echo "fila,tarea,resuelto,tool_calls"; cat "$TRABAJO/resultados.csv") \
  | column -s, -t 2>/dev/null || cat "$TRABAJO/resultados.csv"
echo
echo "Seis sesiones no son evidencia: son una demostración. Lo que decide si esto sirve"
echo "es M4, con tres corridas por celda y umbrales fijados antes de correr nada."
echo "Trabajo en: $TRABAJO  (CONSERVAR=1 para no borrarlo)"
