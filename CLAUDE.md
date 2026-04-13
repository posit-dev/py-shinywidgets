# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

shinywidgets is a Python package that renders [ipywidgets](https://ipywidgets.readthedocs.io) inside [Shiny for Python](https://shiny.posit.co/py/) applications. It bridges the Jupyter widget ecosystem with Shiny's reactive framework.

## Development Setup

```sh
uv sync --all-groups
uv run pre-commit install
uv run playwright install chromium
cd js && yarn install && yarn watch
```

## Common Commands

- **Type checking**: `make pyright` (or `make py-check-types`)
- **Linting/formatting check**: `make py-check-format`
- **Auto-format**: `make py-format`
- **Full quality check**: `make check` (format + types + unit tests)
- **Unit tests**: `make test` (or `make test-unit`)
- **Run a single test**: `uv run pytest tests/unit/test_foo.py::test_name`
- **Playwright (browser) tests**: `make test-playwright`
- **All tests**: `make test-all-local`
- **Coverage**: `make coverage`
- **Build package**: `make dist`
- **Build JS**: `cd js && yarn build`
- **Watch JS**: `cd js && yarn watch`

## Architecture

### Communication Layer

The core challenge is establishing bidirectional communication between Python ipywidgets and the browser, mimicking how Jupyter kernels work but using Shiny's session/message infrastructure.

**Python side (`_comm.py`, `_shinywidgets.py`):**
- `ShinyComm` replaces `ipykernel.comm.Comm` - sends widget state via Shiny custom messages (`shinywidgets_comm_open`, `shinywidgets_comm_msg`, `shinywidgets_comm_close`)
- `init_shiny_widget()` hooks into `Widget.on_widget_constructed` to intercept all widget creation and establish comms
- Widget state is serialized with buffer handling for binary data (base64 encoded since Shiny doesn't support binary messages)
- Global state maps in `_shinywidgets.py`: `SESSIONS`, `COMM_MANAGER`, `SESSION_WIDGET_ID_MAP`, `WIDGET_INSTANCE_MAP`

**JavaScript side (`js/src/output.ts`, `js/src/comm.ts`):**
- `OutputManager` extends `@jupyter-widgets/html-manager`'s `HTMLManager` to render widgets
- Custom `ShinyComm` implements the comm protocol using `Shiny.addCustomMessageHandler`
- Custom module loader (`shinyRequireLoader`) handles widget JS dependencies via require.js

### Rendering Pipeline

1. User decorates function with `@render_widget` (or specialized variants like `@render_plotly`)
2. `render_widget_base._render()` calls user function, converts result via `as_widget()`
3. Widget initialization triggers `init_shiny_widget()` which sets up the comm
4. Render returns `{model_id, fill}` to client
5. Client's `IPyWidgetOutput.renderValue()` retrieves model from manager and displays view

### Widget Coercion (`_as_widget.py`)

Not all visualization objects are ipywidgets. `as_widget()` converts:
- **altair**: Chart -> `altair.JupyterChart`
- **bokeh**: Figure -> `jupyter_bokeh.BokehModel`
- **plotly**: `go.Figure` -> `go.FigureWidget`
- **pydeck**: Deck -> `DeckGLWidget` (via `.show()`)

### Dependencies (`_dependencies.py`)

Handles dynamic loading of 3rd party widget JavaScript:
- `require_dependency()` locates widget's nbextension files and creates HTMLDependency
- Configures require.js paths so widgets can load their JS modules
- Falls back to CDN (unpkg.com) if local extension not found

### Layout Integration

`set_layout_defaults()` in `_render_widget_base.py` applies smart defaults for filling layouts:
- Detects user-specified heights to avoid overriding
- Handles package-specific layout APIs (plotly margins, altair container sizing)
- Works with Shiny's fill layout system

## Key Files

- `shinywidgets/_shinywidgets.py` - Widget initialization, session management, `reactive_read()`
- `shinywidgets/_render_widget_base.py` - `@render_widget` base class
- `shinywidgets/_render_widget.py` - Thin renderer subclasses (`render_plotly`, `render_altair`, etc.)
- `shinywidgets/_comm.py` - Shiny-based comm implementation
- `shinywidgets/_as_widget.py` - Widget coercion functions
- `shinywidgets/_dependencies.py` - JS dependency management
- `js/src/output.ts` - Browser-side output binding and message handlers
- `js/src/comm.ts` - Browser-side comm protocol over Shiny message handlers

## Testing

- **Unit tests** (`tests/unit/`): Cover comm transport, serialization, rendering lifecycle, widget coercion, dependencies, reactivity, and layout defaults. Run with `make test-unit`.
- **Playwright tests** (`tests/playwright/`): Browser-based integration tests that spin up real Shiny apps from `tests/apps/` fixtures. Run with `make test-playwright`.
- Pyright type checking excludes `tests/playwright/` (see `pyproject.toml` `[tool.pyright]` config).
- CI runs format, types, and unit tests across Python 3.10-3.14; Playwright tests on 3.12 only.
