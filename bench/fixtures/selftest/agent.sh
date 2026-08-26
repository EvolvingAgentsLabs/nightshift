#!/bin/sh
# Agente FALSO. Simula una corrida para probar el runner, no a nightshift.
#
# Resuelve siempre en S1 y a veces en S0, para que el resumen tenga dos filas distintas
# y la regla de decisión tenga algo que comparar. Los números no significan nada.
task="$1"
row="$2"
mkdir -p state
case "$row" in
  S1) printf 'listo\n' > "state/${task}.fixed"; calls=6 ;;
  S0) case "$task" in
        *1|*3) printf 'listo\n' > "state/${task}.fixed"; calls=14 ;;
        *)     calls=18 ;;
      esac ;;
esac
echo "NIGHTSHIFT_BENCH {\"tool_calls\": ${calls}}"
