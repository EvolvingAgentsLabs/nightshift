.DEFAULT_GOAL := check
SHELL := /usr/bin/env bash

.PHONY: check lint lint-docs lint-code validate-schema test selftest doctor init clean help

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
