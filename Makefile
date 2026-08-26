.DEFAULT_GOAL := check
SHELL := /usr/bin/env bash

.PHONY: check lint-docs validate-schema help

## check: gate del milestone actual (M0)
check: lint-docs validate-schema
	@echo
	@echo "gate M0: OK"

## lint-docs: estructura de la documentación, enlaces internos y límites de M0
lint-docs:
	@./tools/lint-docs.sh

## validate-schema: los ejemplos válidos validan y los inválidos son rechazados
validate-schema:
	@./tools/validate-schema.sh

## help: lista los targets
help:
	@grep -E '^## ' $(MAKEFILE_LIST) | sed 's/^## /  /'
