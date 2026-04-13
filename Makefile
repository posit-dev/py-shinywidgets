.PHONY: help clean clean-build clean-pyc clean-test py-setup py-check-format py-check-types py-check-tests py-check py-check-tox py-build py-format py-coverage py-check-build test test-unit test-playwright test-playwright-coverage test-all-local coverage coverage-ci coverage-combine coverage-html dist install pyright check

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

py-setup: ## [py] sync the development environment with uv
	uv sync --all-groups

py-check-format: ## [py] run Ruff lint and format checks
	uv run ruff check $(PYTHON_PATHS) --config pyproject.toml
	uv run ruff format --check $(PYTHON_PATHS) --config pyproject.toml

py-check-types: ## [py] run pyright type checks
	uv run pyright $(PYRIGHT_PATHS)

py-check-tests: ## [py] run pytest checks
	$(PYTEST_UNIT)

py-check: ## [py] run format, type, and test checks
	$(MAKE) py-check-format
	$(MAKE) py-check-types
	$(MAKE) py-check-tests

py-check-tox: ## [py] run test and type checks across supported Python versions
	uv run tox run-parallel

py-build: ## [py] build the source and wheel distributions
	uv build

py-format: ## [py] apply Ruff fixes and formatting
	uv run ruff check --fix $(PYTHON_PATHS) --config pyproject.toml
	uv run ruff format $(PYTHON_PATHS) --config pyproject.toml

py-coverage: ## [py] run the test suite under coverage
	rm -f .coverage .coverage.*
	uv run coverage run --rcfile "$(REPO_ROOT)/.coveragerc" -m pytest -c "$(REPO_ROOT)/pytest.ini" --confcutdir "$(REPO_ROOT)"
	uv run coverage combine --rcfile "$(REPO_ROOT)/.coveragerc"
	uv run coverage report

py-check-build: ## [py] verify package build metadata is importable
	uv build
	uv run python -c "import shinywidgets; print(shinywidgets.__version__)"

test: py-check-tests ## run pytest quickly with the default environment

test-unit: ## run unit tests only (explicit config/cutoff)
	$(PYTEST_UNIT)

test-playwright: ## run Playwright regression tests
	uv run playwright install chromium
	$(PYTEST_PLAYWRIGHT)

test-all-local: ## run unit tests then Playwright tests (requires browsers installed)
	$(MAKE) test-unit
	$(MAKE) test-playwright

coverage: py-coverage ## run coverage checks

dist: py-build ## build source and wheel distributions
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

install: py-build ## install the built wheel into the uv environment
	uv run pip uninstall -y shinywidgets || true
	uv run pip install dist/shinywidgets*.whl

pyright: py-check-types ## run pyright type checks

check: py-check ## run the full Python quality check suite
