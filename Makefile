.PHONY: help clean clean-build clean-pyc clean-test setup check-format check-types check-tests check check-tox build format coverage check-build test test-unit test-playwright test-playwright-coverage test-all-local coverage-ci coverage-combine coverage-html dist install pyright

.DEFAULT_GOAL := help

REPO_ROOT ?= $(shell git rev-parse --show-toplevel 2>/dev/null || pwd)

PYTHON_PATHS := shinywidgets tests
PYRIGHT_PATHS := shinywidgets tests/__init__.py tests/unit/test_version_metadata.py
PYTEST_UNIT := uv run pytest -c "$(REPO_ROOT)/pytest.ini" --confcutdir "$(REPO_ROOT)"
PYTEST_PLAYWRIGHT := uv run pytest -c "$(REPO_ROOT)/tests/playwright/playwright-pytest.ini" --confcutdir "$(REPO_ROOT)/tests/playwright" "$(REPO_ROOT)/tests/playwright"

define PRINT_HELP_PYSCRIPT
import re
import sys

for line in sys.stdin:
    match = re.match(r"^([a-zA-Z0-9_/-]+):.*?## (.*)$$", line)
    if match:
        target, help = match.groups()
        print(f"{target:20} {help}")
endef
export PRINT_HELP_PYSCRIPT

help: ## show help messages for make targets
	@python3 -c "$$PRINT_HELP_PYSCRIPT" < $(MAKEFILE_LIST)

clean: clean-build clean-pyc clean-test ## remove build, cache, and coverage artifacts

clean-build: ## remove build artifacts
	rm -rf build/ dist/ .eggs/
	find . -name '*.egg-info' -exec rm -rf {} +
	find . -name '*.egg' -exec rm -f {} +

clean-pyc: ## remove Python cache artifacts
	find . -name '*.pyc' -exec rm -f {} +
	find . -name '*.pyo' -exec rm -f {} +
	find . -name '__pycache__' -exec rm -rf {} +

clean-test: ## remove test and coverage artifacts
	rm -rf .tox/ .pytest_cache/ htmlcov/
	rm -f .coverage .coverage.* coverage.xml

setup: ## sync the development environment with uv
	uv sync --all-groups

check-format: ## run Ruff lint and format checks
	uv run ruff check $(PYTHON_PATHS) --config pyproject.toml
	uv run ruff format --check $(PYTHON_PATHS) --config pyproject.toml

check-types: ## run pyright type checks
	uv run pyright $(PYRIGHT_PATHS)

check-tests: ## run pytest checks
	$(PYTEST_UNIT)

check: ## run format, type, and test checks
	$(MAKE) check-format
	$(MAKE) check-types
	$(MAKE) check-tests

check-tox: ## run test and type checks across supported Python versions
	uv run tox run-parallel

build: ## build the source and wheel distributions
	uv build

format: ## apply Ruff fixes and formatting
	uv run ruff check --fix $(PYTHON_PATHS) --config pyproject.toml
	uv run ruff format $(PYTHON_PATHS) --config pyproject.toml

coverage: ## run the test suite under coverage
	rm -f .coverage .coverage.*
	uv run coverage run --rcfile "$(REPO_ROOT)/.coveragerc" -m pytest -c "$(REPO_ROOT)/pytest.ini" --confcutdir "$(REPO_ROOT)"
	uv run coverage combine --rcfile "$(REPO_ROOT)/.coveragerc"
	uv run coverage report

check-build: ## verify package build metadata is importable
	uv build
	uv run python -c "import shinywidgets; print(shinywidgets.__version__)"

test: check-tests ## run pytest quickly with the default environment

test-unit: ## run unit tests only (explicit config/cutoff)
	$(PYTEST_UNIT)

test-playwright: ## run Playwright regression tests
	uv run playwright install chromium
	$(PYTEST_PLAYWRIGHT)

test-all-local: ## run unit tests then Playwright tests (requires browsers installed)
	$(MAKE) test-unit
	$(MAKE) test-playwright

dist: build ## build source and wheel distributions
coverage-combine: ## combine parallel coverage data files into a single .coverage
	uv run coverage combine --rcfile "$(REPO_ROOT)/.coveragerc"

test-playwright-coverage: ## run Playwright tests with subprocess coverage (best-effort; requires coverage installed)
	rm -f .coverage .coverage.*
	COVERAGE_PROCESS_START="$(REPO_ROOT)/.coveragerc" PYTHONPATH="$(REPO_ROOT)" $(PYTEST_PLAYWRIGHT)
	$(MAKE) coverage-combine
	uv run coverage report --rcfile "$(REPO_ROOT)/.coveragerc" -m

coverage-ci: ## generate a CI-friendly coverage report + coverage.xml
	rm -f .coverage .coverage.*
	uv run coverage run --rcfile "$(REPO_ROOT)/.coveragerc" -m pytest -c "$(REPO_ROOT)/pytest.ini" --confcutdir "$(REPO_ROOT)"
	uv run coverage combine --rcfile "$(REPO_ROOT)/.coveragerc"
	uv run coverage report --rcfile "$(REPO_ROOT)/.coveragerc" -m
	uv run coverage xml --rcfile "$(REPO_ROOT)/.coveragerc" -o coverage.xml

coverage-html: ## generate HTML coverage output
	$(MAKE) coverage-combine
	uv run coverage html --rcfile "$(REPO_ROOT)/.coveragerc"

install: build ## install the built wheel into the uv environment
	uv run pip uninstall -y shinywidgets || true
	uv run pip install dist/shinywidgets*.whl

pyright: check-types ## run pyright type checks
