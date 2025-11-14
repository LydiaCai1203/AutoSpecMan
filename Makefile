PYTHON ?= python
PYTHON_BIN := $(shell which $(PYTHON))
VENV ?= .venv
PIP ?= $(VENV)/bin/pip
PY ?= $(VENV)/bin/python

.PHONY: help
help:
	@echo "Targets:"
	@echo "  setup       Create virtualenv and install deps"
	@echo "  run         Run autospecman against current repo"
	@echo "  smoke       JSON + YAML smoke tests"

.PHONY: setup
setup:
	@echo "Using interpreter: $(PYTHON_BIN)"
	@$(PYTHON_BIN) -m venv $(VENV)
	@$(PIP) install --upgrade pip
	@$(PIP) install -r requirements-dev.txt
	@$(PIP) install -e .[extras]

.PHONY: ensure-venv
ensure-venv:
	@if [ ! -x "$(PY)" ]; then $(MAKE) setup; fi

.PHONY: run
run: ensure-venv
	@$(PY) -m autospecman.cli --repo . --format yaml

.PHONY: smoke
smoke: ensure-venv
	@$(PY) -m autospecman.cli --repo . --format json >/tmp/autospecman.json
	@$(PY) -m autospecman.cli --repo . --format yaml >/tmp/autospecman.yaml
	@echo "JSON -> /tmp/autospecman.json"
	@echo "YAML -> /tmp/autospecman.yaml"

