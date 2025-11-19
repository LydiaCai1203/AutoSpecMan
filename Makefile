# 永远使用当前激活的 Python 环境（conda 或其他）
# 不依赖 .venv，直接使用当前激活的 Python
PYTHON ?= python
PYTHON_BIN := $(shell which $(PYTHON))
VENV ?= .venv
# 直接使用当前激活的 Python（conda 或其他）
PIP := $(PYTHON_BIN) -m pip
PY := $(PYTHON_BIN)
REPO ?= .
ifneq ($(origin repo), undefined)
REPO := $(repo)
endif
REPO_NAME = $(notdir $(abspath $(REPO)))
SPEC_DIR ?= specs
RUN_OUT = $(SPEC_DIR)/spec-$(REPO_NAME).yaml
SMOKE_JSON = /tmp/spec-$(REPO_NAME).json
SMOKE_YAML = /tmp/spec-$(REPO_NAME).yaml
SMOKE_AI = /tmp/spec-$(REPO_NAME)-ai.md

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
	@# 检查当前激活的 Python 是否可用
	@if ! $(PY) --version > /dev/null 2>&1; then \
		echo "Error: Python not found at $(PY)"; \
		echo "Please activate your conda environment (e.g., conda activate AutoSpecMan)"; \
		exit 1; \
	fi
	@echo "Using Python: $(PY)"

.PHONY: run
run: ensure-venv
	@mkdir -p $(SPEC_DIR)
	@echo "Generating spec for $(REPO) -> $(RUN_OUT)"
	@$(PY) -m autospecman.cli --repo "$(REPO)" --format yaml --output "$(RUN_OUT)"

.PHONY: smoke
smoke: ensure-venv
	@echo "Generating AI-friendly spec for $(REPO) -> $(SMOKE_AI)"
	@$(PY) -m autospecman.cli --repo "$(REPO)" --format ai --output "$(SMOKE_AI)"

