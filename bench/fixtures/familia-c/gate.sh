#!/bin/sh
# Gate de la tarea. La tarea corre **dentro** de su repositorio, así que el gate también:
# los dos repos son repos git separados con remotes distintos, y ahí es donde nightshift
# calcula el fingerprint. Con un solo git en la raíz, la familia que mide transferencia
# cross-repo no cruzaba nada.
tarea="$NIGHTSHIFT_BENCH_TASK"
case "$tarea" in
  alfa_*) exec python3 -m unittest "tests.test_${tarea#*_}" -q ;;
  beta_*) exec python3 -m unittest "pruebas.prueba_${tarea#*_}" -q ;;
  *) echo "tarea desconocida: $tarea" >&2; exit 2 ;;
esac
