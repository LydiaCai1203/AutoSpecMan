PYTHON ?= python
PYTHON_BIN := $(shell which $(PYTHON))
VENV ?= .venv
PIP ?= $(VENV)/bin/pip
PY ?= $(VENV)/bin/python
REPO ?= .
ifneq ($(origin repo), undefined)
REPO := $(repo)
endif
REPO_NAME = $(notdir $(abspath $(REPO)))
SPEC_DIR ?= specs
RUN_OUT = $(SPEC_DIR)/spec-$(REPO_NAME).yaml
SMOKE_JSON = /tmp/spec-$(REPO_NAME).json
SMOKE_YAML = /tmp/spec-$(REPO_NAME).yaml

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
	@mkdir -p $(SPEC_DIR)
	@echo "Generating spec for $(REPO) -> $(RUN_OUT)"
	@$(PY) -m autospecman.cli --repo "$(REPO)" --format yaml --output "$(RUN_OUT)"

.PHONY: smoke
smoke: ensure-venv
	@echo "Generating JSON spec for $(REPO) -> $(SMOKE_JSON)"
	@$(PY) -m autospecman.cli --repo "$(REPO)" --format json --output "$(SMOKE_JSON)"
	@echo "Generating YAML spec for $(REPO) -> $(SMOKE_YAML)"
	@$(PY) -m autospecman.cli --repo "$(REPO)" --format yaml --output "$(SMOKE_YAML)"

