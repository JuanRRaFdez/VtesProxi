.PHONY: lint format typecheck check test quality policy-check

VENV_BIN := .venv/bin
PYTHON := python
RUFF := ruff
MYPY := mypy

ifneq (,$(wildcard $(VENV_BIN)/python))
PYTHON := $(VENV_BIN)/python
endif

ifneq (,$(wildcard $(VENV_BIN)/ruff))
RUFF := $(VENV_BIN)/ruff
endif

ifneq (,$(wildcard $(VENV_BIN)/mypy))
MYPY := $(VENV_BIN)/mypy
endif
QUALITY_SCOPE := webvtes scripts desktop
POLICY_SLICE ?= slice3
POLICY_PATHS ?= apps/srv_textos
POLICY_DEBT_CLASSES ?= F841 E501
POLICY_BASELINE_TOTAL ?= 0

lint:
	$(RUFF) check $(QUALITY_SCOPE)

format:
	$(RUFF) format $(QUALITY_SCOPE)

typecheck:
	$(MYPY) --config-file pyproject.toml

check:
	$(PYTHON) manage.py check

test:
	$(PYTHON) manage.py test

quality: lint typecheck check test

policy-check:
	$(PYTHON) scripts/ruff_policy_check.py --slice $(POLICY_SLICE) --paths $(POLICY_PATHS) --debt-classes $(POLICY_DEBT_CLASSES) --baseline-total $(POLICY_BASELINE_TOTAL)
