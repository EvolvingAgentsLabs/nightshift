#!/bin/sh
# Gate de la tarea. Los dos repos no comparten ni el nombre del directorio de tests: el
# vocabulario compartido entre A y B es una vía de transferencia que no es la memoria.
tarea="$NIGHTSHIFT_BENCH_TASK"
case "$tarea" in
  alfa_*) cd repo-alfa || exit 1; exec python3 -m unittest "tests.test_${tarea#*_}" -q ;;
  beta_*) cd repo-beta || exit 1; exec python3 -m unittest "pruebas.prueba_${tarea#*_}" -q ;;
  *) echo "tarea desconocida: $tarea" >&2; exit 2 ;;
esac
