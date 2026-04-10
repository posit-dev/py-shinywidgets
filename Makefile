.PHONY: help clean clean-build clean-pyc clean-test py-setup py-check-format py-check-types py-check-tests py-check py-check-tox py-build py-format py-coverage py-check-build test test-playwright coverage dist install pyright check

.DEFAULT_GOAL := help

PYTHON_PATHS := shinywidgets tests
PYRIGHT_PATHS := shinywidgets tests/__init__.py tests/test_version_metadata.py

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
	rm -f .coverage

py-setup: ## [py] sync the development environment with uv
	uv sync --all-groups

py-check-format: ## [py] run Ruff lint and format checks
	uv run ruff check $(PYTHON_PATHS) --config pyproject.toml
	uv run ruff format --check $(PYTHON_PATHS) --config pyproject.toml

py-check-types: ## [py] run pyright type checks
	uv run pyright $(PYRIGHT_PATHS)

py-check-tests: ## [py] run pytest checks
	uv run pytest

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
	uv run coverage run -m pytest
	uv run coverage report

py-check-build: ## [py] verify package build metadata is importable
	uv build
	uv run python -c "import shinywidgets; print(shinywidgets.__version__)"

test: py-check-tests ## run pytest quickly with the default environment

test-playwright: ## run Playwright regression tests
	uv run playwright install chromium
	uv run pytest -c tests/playwright/playwright-pytest.ini tests/playwright

coverage: py-coverage ## run coverage checks

dist: py-build ## build source and wheel distributions

install: py-build ## install the built wheel into the uv environment
	uv run pip uninstall -y shinywidgets || true
	uv run pip install dist/shinywidgets*.whl

pyright: py-check-types ## run pyright type checks

check: py-check ## run the full Python quality check suite
