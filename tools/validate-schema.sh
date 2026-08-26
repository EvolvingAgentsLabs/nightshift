#!/usr/bin/env bash
# Gate de M0: los ejemplos de schema/examples/valid/ validan contra el esquema y los
# de schema/examples/invalid/ son rechazados. Un inválido que empieza a validar es un
# agujero en el esquema y rompe el gate igual que un válido que deja de validar.
set -uo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
SCHEMA="$ROOT/schema/trajectory.v1.json"
PINNED_VERSION="0.33.0"

if command -v check-jsonschema >/dev/null 2>&1; then
  VALIDATE=(check-jsonschema)
elif command -v uvx >/dev/null 2>&1; then
  VALIDATE=(uvx --quiet "check-jsonschema@${PINNED_VERSION}")
elif command -v pipx >/dev/null 2>&1; then
  VALIDATE=(pipx run "check-jsonschema==${PINNED_VERSION}")
else
  echo "ERROR: falta check-jsonschema. Instalá con 'uv tool install check-jsonschema' o 'pipx install check-jsonschema'." >&2
  exit 127
fi

run_validator() { "${VALIDATE[@]}" --schemafile "$SCHEMA" "$1" >/dev/null 2>&1; }

fail=0
pass=0

echo "== esquema =="
if ! "${VALIDATE[@]}" --check-metaschema "$SCHEMA" >/dev/null 2>&1; then
  echo "  FALLA  el esquema no cumple su metaschema: $SCHEMA"
  fail=$((fail + 1))
else
  echo "  ok     trajectory.v1.json cumple el metaschema"
  pass=$((pass + 1))
fi

echo "== ejemplos válidos (deben validar) =="
shopt -s nullglob
for f in "$ROOT"/schema/examples/valid/*.json; do
  if run_validator "$f"; then
    echo "  ok     ${f#"$ROOT"/}"
    pass=$((pass + 1))
  else
    echo "  FALLA  ${f#"$ROOT"/} debería validar y no valida"
    "${VALIDATE[@]}" --schemafile "$SCHEMA" "$f" 2>&1 | sed 's/^/           /'
    fail=$((fail + 1))
  fi
done

echo "== ejemplos inválidos (deben ser rechazados) =="
for f in "$ROOT"/schema/examples/invalid/*.json; do
  if run_validator "$f"; then
    echo "  FALLA  ${f#"$ROOT"/} debería ser rechazado y valida — agujero en el esquema"
    fail=$((fail + 1))
  else
    echo "  ok     ${f#"$ROOT"/} rechazado"
    pass=$((pass + 1))
  fi
done

echo
if [ "$fail" -eq 0 ]; then
  echo "validate-schema: OK ($pass comprobaciones)"
  exit 0
fi
echo "validate-schema: $fail fallo(s), $pass ok"
exit 1
