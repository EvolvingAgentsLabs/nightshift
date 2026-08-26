#!/bin/sh
# Gate del fixture sintético: sale 0 si la tarea quedó "arreglada".
# El criterio de resolución del pre-registro es exactamente esto — un comando que sale 0
# o no — y no el juicio de un modelo.
[ -f "state/${NIGHTSHIFT_BENCH_TASK}.fixed" ]
