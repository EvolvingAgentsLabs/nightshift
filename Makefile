.DEFAULT_GOAL := check
SHELL := /usr/bin/env bash

.PHONY: check lint lint-docs lint-code validate-schema test selftest dream-selftest bench-selftest bench-fixtures bench-check simulate dogfood doctor init clean help

## check: el gate completo. Un gate es un script, no un juicio.
check: lint validate-schema test selftest
	@echo
	@echo "gate: OK"

## lint: documentación + invariantes del código
lint: lint-docs lint-code

## lint-docs: estructura de la documentación y enlaces internos
lint-docs:
	@./tools/lint-docs.sh

## lint-code: stdlib pura, sin red, coexistencia con Auto Memory, plugin bien formado
lint-code:
	@./tools/lint-code.sh

## validate-schema: los ejemplos válidos validan y los inválidos son rechazados
validate-schema:
	@./tools/validate-schema.sh

## test: suite unitaria (stdlib unittest, sin dependencias)
test:
	@python3 -m unittest discover -s tests -t . -q

## selftest: replay end-to-end de los 7 hooks contra un store desechable
selftest:
	@./bin/nightshift selftest

## dream-selftest: gate de M3-a. Necesita un modelo local, por eso no está en `check`
dream-selftest:
	@./bin/nightshift dream --selftest

## dogfood: el gate del pivot. Afirma sobre el store REAL, no sobre uno desechable
dogfood: check
	@echo
	@./bin/nightshift doctor
	@echo
	@./bin/nightshift audit
	@echo
	@./bin/nightshift status
	@echo
	@echo "dogfood: OK — y lo que esto NO dice está en doc/HANDOFF.md §0-bis"

## simulate: ensayo end-to-end con sesiones sintéticas. NO cierra el gate de M1 ni el de M3
simulate:
	@./bin/nightshift simulate

## bench-selftest: gate del runner de M4. No corre el benchmark: prueba el runner
bench-selftest:
	@./bin/nightshift bench selftest

## bench-fixtures: cada tarea de cada fixture falla antes y la resuelve su fix de referencia
bench-fixtures:
	@NIGHTSHIFT_ROOT=$(CURDIR) ./bin/nightshift bench fixtures

## bench-check: qué le falta al pre-registro para poder correr M4
bench-check:
	@./bin/nightshift bench check

## doctor: auto-diagnóstico de invariantes en runtime
doctor:
	@./bin/nightshift doctor

## init: crear la config local con los deny_paths por defecto
init:
	@./bin/nightshift init

## clean: borrar bytecode
clean:
	@find . -name '__pycache__' -type d -not -path './.git/*' -exec rm -rf {} + 2>/dev/null || true

## help: lista los targets
help:
	@grep -E '^## ' $(MAKEFILE_LIST) | sed 's/^## /  /'
