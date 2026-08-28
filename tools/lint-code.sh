#!/usr/bin/env bash
# Invariantes del código. No es estilo: cada chequeo defiende una prohibición del
# proyecto (CLAUDE.md) o una condición de éxito de la spec.
set -uo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT" || exit 1

fail=0
err() { echo "  FALLA  $*"; fail=$((fail + 1)); }
ok()  { echo "  ok     $*"; }

echo "== compila =="
if python3 -m compileall -q nightshift tests >/dev/null 2>&1; then
  ok "nightshift/ y tests/ compilan"
else
  err "error de sintaxis"
  python3 -m compileall -q nightshift tests
fi
find . -name '__pycache__' -type d -not -path './.git/*' -exec rm -rf {} + 2>/dev/null

echo "== sólo librería estándar (spec §2.2: sin dependencias) =="
third_party=$(python3 - <<'PY'
import ast, pathlib, sys
try:
    stdlib = set(sys.stdlib_module_names)
except AttributeError:
    stdlib = None
local = {"nightshift", "tests"}
bad = []
# `pathlib` no expande llaves: el patrón `{nightshift,tests}/**/*.py` que había acá
# devolvía **cero** archivos y el chequeo entero se apoyaba en el `or` de atrás sin que
# nadie lo notara. Un linter que pasa porque su lista quedó vacía no está defendiendo
# nada, así que la lista se arma explícita y se afirma que no está vacía.
archivos = sorted(list(pathlib.Path("nightshift").rglob("*.py"))
                  + list(pathlib.Path("tests").rglob("*.py")))
if not archivos:
    print("SIN ARCHIVOS: el chequeo de stdlib no miró nada")
    raise SystemExit(0)
for path in archivos:
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            names = [a.name.split(".")[0] for a in node.names]
        elif isinstance(node, ast.ImportFrom):
            if node.level:      # import relativo: local por definición
                continue
            names = [(node.module or "").split(".")[0]]
        else:
            continue
        for name in names:
            if not name or name in local:
                continue
            if stdlib is not None and name not in stdlib:
                bad.append("%s:%d %s" % (path, node.lineno, name))
print("\n".join(sorted(set(bad))))
PY
)
if [ "$third_party" = "SIN ARCHIVOS: el chequeo de stdlib no miró nada" ]; then
  err "el chequeo de stdlib no encontró un solo archivo: pasó por vacío, no por limpio"
elif [ -z "$third_party" ]; then
  ok "ningún import de tercero"
else
  echo "$third_party" | sed 's/^/           /'
  err "imports de tercero: nightshift corre con stdlib pura"
fi

echo "== sin red (spec §2.2: sin dependencias de API remota) =="
net=$(grep -rnE '^\s*(import|from)\s+(socket|ssl|urllib|http|ftplib|smtplib|telnetlib|requests|httpx|aiohttp)\b' nightshift/ || true)
if [ -z "$net" ]; then
  ok "ningún módulo de red importado en nightshift/"
else
  echo "$net" | sed 's/^/           /'
  err "nightshift no habla con la red"
fi

echo "== coexistencia con Auto Memory (spec §1.3.4) =="
# Tres archivos pueden nombrar el árbol nativo, y sólo por estos motivos:
#   config.py  -> el guard que lo rechaza      context.py -> memory_signal(), sólo lectura
#   cli.py     -> el doctor, que afirma que el guard rechaza
# Cualquier otro archivo nombrándolo es una vía de escritura sin auditar.
mem=$(grep -rn '\.claude/projects' nightshift/ | grep -vE '^nightshift/(config|context|cli)\.py:' || true)
if [ -z "$mem" ]; then
  ok "sólo config.py, context.py y cli.py nombran el árbol nativo"
else
  echo "$mem" | sed 's/^/           /'
  err "el árbol de Auto Memory sólo puede tocarse desde config.py, context.py y cli.py"
fi
grep -q 'assertRaises(PermissionError)' tests/test_coexistence.py \
  && ok "el guard tiene test negativo" || err "falta el test que prueba que el guard rechaza"
grep -q 'AUTO_MEMORY_RE' nightshift/config.py \
  && ok "el guard existe en config.py" || err "falta AUTO_MEMORY_RE en config.py"

echo "== los hooks no ensucian stdout =="
bare=$(grep -nE '^\s*print\(' nightshift/hook.py || true)
if [ -z "$bare" ]; then
  ok "hook.py no imprime fuera de _emit"
else
  echo "$bare" | sed 's/^/           /'
  err "stdout de un hook debe ser JSON válido o nada"
fi
grep -q 'return 0' nightshift/hook.py && ok "hook.main siempre devuelve 0" \
  || err "hook.main debe salir 0 siempre (spec §7.2)"

echo "== plugin =="
for f in .claude-plugin/plugin.json hooks/hooks.json bin/ns-hook bin/nightshift; do
  [ -f "$f" ] && ok "$f" || err "falta $f"
done
for f in bin/ns-hook bin/nightshift tools/*.sh; do
  [ -x "$f" ] && ok "$f ejecutable" || err "$f no es ejecutable"
done
events=$(jq -r '.hooks | keys[]' hooks/hooks.json 2>/dev/null | sort)
known=$(python3 -c "import sys; sys.path.insert(0,'.'); from nightshift.hook import EVENTS; print('\n'.join(sorted(EVENTS)))")
unknown=$(comm -23 <(echo "$events") <(echo "$known"))
uncovered=$(comm -13 <(echo "$events") <(echo "$known"))
[ -z "$unknown" ] && ok "hooks.json sólo declara eventos que hook.py maneja" \
  || err "hooks.json declara eventos desconocidos: $(echo "$unknown" | tr '\n' ' ')"
[ -z "$uncovered" ] && ok "todos los handlers están declarados en hooks.json" \
  || err "handlers sin declarar en hooks.json: $(echo "$uncovered" | tr '\n' ' ')"

for skill in skills/*/SKILL.md; do
  head -1 "$skill" | grep -q '^---$' && grep -q '^description:' "$skill" \
    && ok "${skill} tiene frontmatter con description" \
    || err "${skill}: falta frontmatter o description"
done

echo "== sin manifiestos de dependencias =="
for f in pyproject.toml requirements.txt setup.py setup.cfg Pipfile poetry.lock; do
  [ -f "$f" ] && err "nightshift no declara dependencias: $f"
done
ok "sin manifiestos de dependencias"

echo
if [ "$fail" -eq 0 ]; then
  echo "lint-code: OK"
  exit 0
fi
echo "lint-code: $fail fallo(s)"
exit 1
