shinywidgets
================

Render [ipywidgets](https://ipywidgets.readthedocs.io/en/stable/) inside a
[Shiny](https://shiny.rstudio.com/py) (for Python) app.

See the [Jupyter Widgets](https://shiny.posit.co/py/docs/jupyter-widgets.html) article on the Shiny for Python website for more details.

## Installation

```sh
pip install shinywidgets
```

The `@render_*` decorators for third-party widget packages (e.g.,
`@render_plotly`, `@render_bokeh`) require those packages, which aren't
installed by default. Each decorator has a matching *extra* that installs
everything it needs:

| Decorator | Install command |
| --- | --- |
| `@render_altair` | `pip install 'shinywidgets[altair]'` |
| `@render_bokeh` | `pip install 'shinywidgets[bokeh]'` |
| `@render_holoviews` | `pip install 'shinywidgets[holoviews]'` |
| `@render_ipyaladin` | `pip install 'shinywidgets[ipyaladin]'` |
| `@render_ipycanvas` | `pip install 'shinywidgets[ipycanvas]'` |
| `@render_ipydatagrid` | `pip install 'shinywidgets[ipydatagrid]'` |
| `@render_itables` | `pip install 'shinywidgets[itables]'` |
| `@render_jscatter` | `pip install 'shinywidgets[jscatter]'` |
| `@render_k3d` | `pip install 'shinywidgets[k3d]'` |
| `@render_keplergl` | `pip install 'shinywidgets[keplergl]'` |
| `@render_lonboard` | `pip install 'shinywidgets[lonboard]'` (Python < 3.15) |
| `@render_maplibre` | `pip install 'shinywidgets[maplibre]'` |
| `@render_matplotlib` | `pip install 'shinywidgets[matplotlib]'` |
| `@render_panel` | `pip install 'shinywidgets[panel]'` |
| `@render_plotly` | `pip install 'shinywidgets[plotly]'` |
| `@render_plotnine` | `pip install 'shinywidgets[plotnine]'` |

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
make check
make test-playwright
make build
```
