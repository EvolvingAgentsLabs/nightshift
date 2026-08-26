#!/bin/sh
# Clasificador FALSO de la familia D. En el benchmark real esto compara las memorias
# inyectadas contra un ground truth hecho a mano al preparar el fixture (PREREG §3-D);
# acá sólo devuelve un número fijo por fila para probar que el runner lo lee y lo anota.
case "$NIGHTSHIFT_BENCH_ROW" in
  S1) echo 'NIGHTSHIFT_BENCH {"false_stale_ratio": 0.10}' ;;
  *)  echo 'NIGHTSHIFT_BENCH {"false_stale_ratio": 0.40}' ;;
esac
