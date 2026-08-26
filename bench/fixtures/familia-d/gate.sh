#!/bin/sh
exec python3 -m unittest "tests.${NIGHTSHIFT_BENCH_TASK}" -q
