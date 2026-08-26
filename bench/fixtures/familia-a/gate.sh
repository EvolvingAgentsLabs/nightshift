#!/bin/sh
# Gate de la tarea: corre SÓLO el test de esta tarea.
# El criterio de resolución del pre-registro es esto y nada más — un comando que sale 0 o
# no sale 0. Sin juicio de modelo (PREREG §3-A).
exec python3 -m unittest "tests.${NIGHTSHIFT_BENCH_TASK}" -q
