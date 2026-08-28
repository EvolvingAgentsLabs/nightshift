#!/bin/sh
# El release del servicio. Doce pasos, y ninguno documenta al siguiente.
#
# Cada paso imprime lo que hizo. El que falla imprime por qué **a medias**: el mensaje dice
# qué chequeo no pasó, nunca qué hay que hacer para que pase. Eso no es crueldad de fixture:
# es cómo se ven los scripts de release de verdad, escritos por alguien que ya sabía.
set -e
cd "$(dirname "$0")/.." || exit 2

paso() { printf '  [%2d/12] %s\n' "$1" "$2"; }

# La métrica de esta familia se cuenta sola: cuántas veces hubo que correr el release
# hasta que salió en verde. Es determinista y no la juzga nadie.
mkdir -p .estado
CORRIDAS=$(( $(cat .estado/corridas 2>/dev/null || echo 0) + 1 ))
echo "$CORRIDAS" > .estado/corridas

paso 1 "verificando el arbol limpio";        [ -z "$SUCIO" ] || { echo "el arbol tiene cambios"; exit 1; }
paso 2 "leyendo la version";                 VERSION=$(cat app/VERSION)
paso 3 "resolviendo dependencias";           :
paso 4 "compilando";                         :
paso 5 "corriendo la suite";                 python3 -m unittest discover -s tests -t . -q 2>/dev/null || true
paso 6 "generando el changelog";             :
paso 7 "aplicando migraciones"
python3 migraciones/aplicar.py || exit 7
paso 8 "firmando el artefacto"
[ -n "$FIRMA_KEY" ] || { echo "falta la clave de firma"; exit 8; }
paso 9 "subiendo el artefacto";              :
paso 10 "etiquetando";                       :
paso 11 "avisando al canal";                 :
paso 12 "listo: $VERSION"
