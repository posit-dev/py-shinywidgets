shinywidgets
================

Render [ipywidgets](https://ipywidgets.readthedocs.io/en/stable/) inside a
[Shiny](https://shiny.rstudio.com/py) (for Python) app.

See the [Jupyter Widgets](https://shiny.posit.co/py/docs/jupyter-widgets.html) article on the Shiny for Python website for more details.

## Installation

```sh
pip install shinywidgets
```

## Development

If you want to do development on `{shinywidgets}`, run:

```sh
uv sync --all-groups
uv run pre-commit install
uv run playwright install chromium
cd js && yarn watch
```

If you need the older editable-install flow for tooling compatibility, this
also works:

```sh
pip install -e ".[dev]"
```

Common Python workflows:

```sh
make py-check
make test-playwright
make py-build
```
