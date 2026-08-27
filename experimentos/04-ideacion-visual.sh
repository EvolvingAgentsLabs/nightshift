#!/bin/sh
# Experimento 4 — Un bloque `ideate` antes de abstraer
#
# La idea (de Matías): antes de razonar, **idear** — describir el mecanismo como lo hace
# una persona, en imágenes: un diagrama, una escena, una animación. Cómo un algoritmo
# recorre el área bajo una curva; cómo un banco de filtros deforma una señal; qué le pasa
# a un dato al atravesar una función. Y recién después abstraer, desde el dibujo.
#
# La hipótesis que se puede falsar: **el dibujo de un mecanismo es invariante entre
# síntomas de un modo que la prosa no lo es.** Diez bugs con una causa compartida y diez
# síntomas distintos se describen con diez prosas distintas — pero, si la hipótesis vale,
# con el mismo dibujo. Y una abstracción hecha desde el dibujo tendría que transferir a un
# síntoma que nunca vio.
#
# Eso es exactamente lo que le faltó al experimento 01: con una trayectoria, dream abstrae
# ESE caso y no la causa compartida. El patrón sale fiel y poco portable.
#
# Tres fases:
#   1. Se capturan trayectorias reales sobre los primeros bugs de la familia A.
#   2. Se consolida DOS VECES desde las mismas trayectorias: prompt actual vs prompt con
#      un bloque `ideate` adelante. Mismo corpus, misma temperatura de azar, una variable.
#   3. Prueba ciega: un bug con OTRO síntoma, que ninguna de las dos vio. Tres sesiones —
#      sin memoria, con el patrón del prompt actual, con el patrón ideado.
#
# No toca `nightshift/`: el bloque `ideate` vive acá, en el experimento. Si resulta que
# sirve, entra al plugin por el camino normal y no antes.
#
# Corre sobre copias desechables y stores desechables. No suma al gate de M1.
set -eu

RAIZ=$(cd "$(dirname "$0")/.." && pwd)
FIXTURE="$RAIZ/bench/fixtures/familia-a"
MODELO="${MODELO:-sonnet}"
APRENDE="${APRENDE:-test_01_indice test_02_dedup test_03_orden}"
CIEGA="${CIEGA:-test_09_reporte}"
TRABAJO=$(mktemp -d /tmp/nightshift-exp4-XXXXXX)
STORE="$TRABAJO/store"

limpiar() { [ "${CONSERVAR:-0}" = "1" ] || rm -rf "$TRABAJO"; }
trap limpiar EXIT

prompt_de() {
  python3 -c "
import json
d = json.load(open('$FIXTURE/fixture.json'))
print(next(t['prompt'] for t in d['tasks'] if t['id'] == '$1'))"
}

repo_limpio() {
  repo="$1"
  cp -R "$FIXTURE" "$repo"
  rm -rf "$repo/.referencia" "$repo/__pycache__" "$repo/tests/__pycache__"
  ( cd "$repo" && git init -q -b main \
      && git remote add origin https://example.invalid/registro-fixture.git \
      && git add -A && git -c user.email=x@y.z -c user.name=x commit -qm fixture )
}

# Una sesión con el plugin cargado, para que capture. Devuelve tool calls por stdout.
sesion_capturando() {
  tarea="$1"; repo="$TRABAJO/aprende-$tarea"
  repo_limpio "$repo"
  salida=$(cd "$repo" && NIGHTSHIFT_HOME="$STORE" claude -p "$(prompt_de "$tarea")" \
    --model "$MODELO" --output-format stream-json --verbose \
    --permission-mode bypassPermissions \
    --plugin-dir "$RAIZ" 2>/dev/null || true)
  printf '%s' "$salida" | python3 -c "
import json, sys
n = 0
for l in sys.stdin:
    l = l.strip()
    if not l.startswith('{'):
        continue
    try: d = json.loads(l)
    except ValueError: continue
    if d.get('type') == 'assistant':
        n += sum(1 for b in d.get('message', {}).get('content') or []
                 if b.get('type') == 'tool_use')
print(n)"
}

echo "Experimento 4 — un bloque ideate antes de abstraer"
echo "modelo: $MODELO · aprende con: $APRENDE · prueba ciega: $CIEGA"
echo

echo "── Fase 1 · trayectorias reales ──────────────────────────────────────────────"
NIGHTSHIFT_HOME="$STORE" "$RAIZ/bin/nightshift" init >/dev/null
for t in $APRENDE; do
  printf '  %-18s ' "$t"
  echo "tool_calls=$(sesion_capturando "$t")"
done
NIGHTSHIFT_HOME="$STORE" python3 -c "
import sys; sys.path.insert(0, '$RAIZ')
from nightshift import store
c = store.connect()
print('  capturadas: %d trayectoria(s), %d paso(s)'
      % (c.execute('SELECT COUNT(*) c FROM trajectories').fetchone()['c'],
         c.execute('SELECT COUNT(*) c FROM steps').fetchone()['c']))"
echo

echo "── Fase 2 · el mismo corpus, dos prompts ─────────────────────────────────────"
NIGHTSHIFT_HOME="$STORE" python3 "$RAIZ/experimentos/ideate.py" \
  --raiz "$RAIZ" --salida "$TRABAJO" --modelo "$MODELO"
echo

echo "── Fase 3 · prueba ciega sobre un síntoma que ninguno vio ────────────────────"
for brazo in sin-memoria control ideado; do
  repo="$TRABAJO/ciega-$brazo"
  repo_limpio "$repo"
  antes=$(cd "$repo" && NIGHTSHIFT_BENCH_TASK="$CIEGA" sh gate.sh >/dev/null 2>&1 \
            && echo 0 || echo 1)
  preambulo=""
  [ "$brazo" != "sin-memoria" ] && preambulo=$(cat "$TRABAJO/inyeccion-$brazo.txt")
  salida=$(cd "$repo" && claude -p "$preambulo$(prompt_de "$CIEGA")" \
    --model "$MODELO" --output-format stream-json --verbose \
    --permission-mode bypassPermissions \
    2>/dev/null || true)
  despues=$(cd "$repo" && NIGHTSHIFT_BENCH_TASK="$CIEGA" sh gate.sh >/dev/null 2>&1 \
              && echo 0 || echo 1)
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
  resuelto=no
  [ "$antes" != "0" ] && [ "$despues" = "0" ] && resuelto=sí
  printf '  %-12s gate %s→%s  resuelto=%-3s tool_calls=%s\n' \
    "$brazo" "$antes" "$despues" "$resuelto" "$calls"
done
echo
echo "Tres sesiones no son evidencia: son una demostración. Un brazo por celda no puede"
echo "distinguir nada — el experimento 01 midió 8, 13 y 10 tool calls en la MISMA tarea"
echo "sin ninguna memoria. Lo que sí se lee acá son los dos patrones, uno al lado del otro."
echo "Trabajo en: $TRABAJO  (CONSERVAR=1 para no borrarlo)"
