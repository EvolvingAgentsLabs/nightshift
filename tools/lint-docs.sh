#!/usr/bin/env bash
# Gate de M0: estructura de la documentación, enlaces internos y límites del milestone.
# No valida prosa. Valida que el repo sea lo que dice ser.
set -uo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT" || exit 1

fail=0
err() { echo "  FALLA  $*"; fail=$((fail + 1)); }
ok()  { echo "  ok     $*"; }

# ---------------------------------------------------------------- 1. archivos
echo "== archivos requeridos =="
REQUIRED=(
  README.md
  README.es.md
  CLAUDE.md
  LATER.md
  LICENSE
  NOTICE
  Makefile
  doc/00-spec.md
  doc/PLAN-v0.3.md
  doc/adr/ADR-001-no-competir-con-auto-dream.md
  doc/adr/ADR-002-verify-gate.md
  schema/trajectory.v1.json
  schema/examples/README.md
  bench/PREREG.md
)
for f in "${REQUIRED[@]}"; do
  [ -f "$f" ] && ok "$f" || err "falta $f"
done

for d in schema/examples/valid schema/examples/invalid; do
  n=$(find "$d" -maxdepth 1 -name '*.json' 2>/dev/null | wc -l | tr -d ' ')
  [ "$n" -gt 0 ] && ok "$d/ tiene $n ejemplo(s)" || err "$d/ está vacío"
done

# ------------------------------------------------- 2. límites del milestone M0
echo "== límites de M0 (sólo documentación) =="
py=$(find . -name '*.py' -not -path './.git/*' 2>/dev/null)
[ -z "$py" ] && ok "sin código Python" || err "M0 no admite código Python: $py"

for f in pyproject.toml requirements.txt setup.py setup.cfg Pipfile package.json; do
  [ -f "$f" ] && err "M0 no admite dependencias declaradas: $f"
done
ok "sin manifiestos de dependencias"

if [ -d .claude/hooks ] || [ -f .claude/settings.json ]; then
  err "M0 no toca hooks: encontrado .claude/hooks o .claude/settings.json"
else
  ok "sin hooks instalados"
fi

# ------------------------------------------------------ 3. JSON bien formado
echo "== JSON =="
while IFS= read -r f; do
  if jq -e . "$f" >/dev/null 2>&1; then ok "${f#./}"; else err "JSON malformado: ${f#./}"; fi
done < <(find . -name '*.json' -not -path './.git/*' | sort)

# ------------------------------------------------------- 4. enlaces internos
echo "== enlaces internos =="
links=0
while IFS= read -r md; do
  dir=$(dirname "$md")
  while IFS= read -r target; do
    [ -z "$target" ] && continue
    case "$target" in
      http://*|https://*|mailto:*) continue ;;
    esac
    links=$((links + 1))
    anchor="${target#*#}"
    path="${target%%#*}"
    if [ -z "$path" ]; then
      # enlace a una sección del mismo archivo
      slug=$(grep -E '^#{1,6} ' "$md" \
        | sed -E 's/^#+ //' \
        | tr '[:upper:]' '[:lower:]' \
        | sed -E 's/[^a-z0-9 -]//g; s/ +/-/g' \
        | grep -Fx "$anchor" || true)
      [ -n "$slug" ] || err "ancla inexistente en ${md#./}: #$anchor"
    elif [ ! -e "$dir/$path" ]; then
      err "enlace roto en ${md#./}: $target"
    fi
  done < <(grep -oE '\]\([^)]+\)' "$md" | sed -E 's/^\]\(//; s/\)$//')
done < <(find . -name '*.md' -not -path './.git/*' | sort)
ok "$links enlaces internos comprobados"

# ------------------------------------------------------ 5. contenido esperado
echo "== contenido esperado =="
grep -q '| Versión | 0.3 |' doc/00-spec.md \
  && ok "spec declara v0.3" || err "doc/00-spec.md no declara 'Versión | 0.3'"
grep -q 'Changelog v0.2 → v0.3' doc/00-spec.md \
  && ok "spec tiene changelog v0.2 → v0.3" || err "doc/00-spec.md no tiene changelog"

for r in README.md README.es.md; do
  missing=""
  for row in '| A |' '| B |' '| C |' '| D |' '| E |'; do
    grep -qF "$row" "$r" || missing="$missing $row"
  done
  [ -z "$missing" ] && ok "$r tiene la matriz completa (A–E)" \
                    || err "$r: faltan filas de la matriz:$missing"
done

for adr in doc/adr/ADR-*.md; do
  missing=""
  for s in '## Contexto' '## Decisión' '## Consecuencias' '## Alternativas consideradas'; do
    grep -qF "$s" "$adr" || missing="$missing '$s'"
  done
  grep -qE '^\| Estado \|' "$adr" || missing="$missing 'Estado'"
  [ -z "$missing" ] && ok "${adr#doc/adr/} completo" \
                    || err "${adr#doc/adr/}: faltan secciones:$missing"
done

for fam in '### A — Bug recurrente variado' '### C — Transferencia cross-repo' '### D — Precisión de consolidación'; do
  grep -qF "$fam" bench/PREREG.md || err "bench/PREREG.md: falta la familia '$fam'"
done
ok "PREREG declara las tres familias"

n_todo=$(grep -c 'TODO(Matias)' bench/PREREG.md)
[ "$n_todo" -gt 0 ] && ok "PREREG tiene $n_todo umbral(es) sin fijar, marcados TODO(Matias)" \
                    || err "bench/PREREG.md no tiene ningún TODO(Matias): ¿alguien inventó números?"

grep -qF 'Registro de enmiendas' bench/PREREG.md \
  && ok "PREREG tiene registro de enmiendas" || err "bench/PREREG.md sin registro de enmiendas"

# -------------------------------------------- 6. TODO sin dueño / formato
echo "== higiene =="
orphan=$(grep -rnE '\b(TODO|FIXME|XXX)\b' --include='*.md' --include='*.json' \
           --exclude-dir=.git . | grep -vE 'TODO\([A-Za-z]+\)' | grep -v 'tools/' || true)
if [ -n "$orphan" ]; then
  echo "$orphan" | sed 's/^/           /'
  err "TODO/FIXME sin dueño: usá TODO(Nombre)"
else
  ok "todos los TODO tienen dueño"
fi

ws=$(grep -rlnE ' +$' --include='*.md' --include='*.json' --exclude-dir=.git . || true)
[ -z "$ws" ] && ok "sin espacios al final de línea" \
             || err "espacios al final de línea en: $(echo "$ws" | tr '\n' ' ')"

nonl=""
while IFS= read -r f; do
  [ -s "$f" ] && [ "$(tail -c 1 "$f" | wc -l)" -eq 0 ] && nonl="$nonl ${f#./}"
done < <(find . \( -name '*.md' -o -name '*.json' \) -not -path './.git/*')
[ -z "$nonl" ] && ok "todos los archivos terminan en newline" \
               || err "sin newline final:$nonl"

echo
if [ "$fail" -eq 0 ]; then
  echo "lint-docs: OK"
  exit 0
fi
echo "lint-docs: $fail fallo(s)"
exit 1
