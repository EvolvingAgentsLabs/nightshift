#!/bin/sh
# Gate de la familia G: el release sale 0, y se cuenta cuántas corridas hicieron falta.
#
# La métrica no la juzga nadie: `repo/.estado/corridas` la lleva el propio script del
# release. Un agente que sabe el procedimiento entero lo deja verde en una o dos corridas;
# uno que lo descubre a los golpes necesita una por cada cosa que no sabía.
cd "$(dirname "$0")/repo" || exit 2
sh scripts/release.sh
estado=$?
printf 'corridas del release: %s\n' "$(cat .estado/corridas 2>/dev/null || echo 0)"
exit "$estado"
