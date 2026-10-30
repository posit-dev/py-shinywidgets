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
| `@render_embedding_atlas` | `pip install 'shinywidgets[embedding_atlas]'` (Python 3.11+) |
| `@render_bqplot` | `pip install 'shinywidgets[bqplot]'` |
| `@render_drawdata` | `pip install 'shinywidgets[drawdata]'` |
| `@render_geolibre` | `pip install 'shinywidgets[geolibre]'` (Python ≥ 3.11) |
| `@render_holoviews` | `pip install 'shinywidgets[holoviews]'` |
| `@render_ipyaladin` | `pip install 'shinywidgets[ipyaladin]'` |
| `@render_ipycanvas` | `pip install 'shinywidgets[ipycanvas]'` |
| `@render_ipycytoscape` | `pip install 'shinywidgets[ipycytoscape]'` |
| `@render_ipydatagrid` | `pip install 'shinywidgets[ipydatagrid]'` |
| `@render_ipyfilechooser` | `pip install 'shinywidgets[ipyfilechooser]'` |
| `@render_ipyleaflet` | `pip install 'shinywidgets[ipyleaflet]'` |
| `@render_ipysigma` | `pip install 'shinywidgets[ipysigma]'` |
| `@render_ipyvolume` | `pip install 'shinywidgets[ipyvolume]'` |
| `@render_itables` | `pip install 'shinywidgets[itables]'` |
| `@render_jscatter` | `pip install 'shinywidgets[jscatter]'` |
| `@render_k3d` | `pip install 'shinywidgets[k3d]'` |
| `@render_keplergl` | `pip install 'shinywidgets[keplergl]'` |
| `@render_leafmap` | `pip install 'shinywidgets[leafmap]'` |
| `@render_lonboard` | `pip install 'shinywidgets[lonboard]'` (Python < 3.15) |
| `@render_maplibre` | `pip install 'shinywidgets[maplibre]'` |
| `@render_matplotlib` | `pip install 'shinywidgets[matplotlib]'` |
| `@render_mols2grid` | `pip install 'shinywidgets[mols2grid]'` |
| `@render_nglview` | `pip install 'shinywidgets[nglview]'` |
| `@render_mosaic_widget` | `pip install 'shinywidgets[mosaic_widget]'` |
| `@render_niivue` | `pip install 'shinywidgets[niivue]'` |
| `@render_obsplot` | `pip install 'shinywidgets[obsplot]'` |
| `@render_panel` | `pip install 'shinywidgets[panel]'` |
| `@render_perspective` | `pip install 'shinywidgets[perspective]'` |
| `@render_plotly` | `pip install 'shinywidgets[plotly]'` |
| `@render_plotnine` | `pip install 'shinywidgets[plotnine]'` |
| `@render_pygwalker` | `pip install 'shinywidgets[pygwalker]'` |
| `@render_pythreejs` | `pip install 'shinywidgets[pythreejs]'` |
| `@render_pyvista` | `pip install 'shinywidgets[pyvista]'` (Python < 3.15) |
| `@render_quak` | `pip install 'shinywidgets[quak]'` |
| `@render_reactable` | `pip install 'shinywidgets[reactable]'` |
| `@render_vizarr` | `pip install 'shinywidgets[vizarr]'` |
| `@render_rerun` | `pip install 'shinywidgets[rerun]'` (Python >= 3.11) |


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
| `@render_embedding_atlas` | `pip install 'shinywidgets[embedding_atlas]'` (Python 3.11+) |
| `@render_bqplot` | `pip install 'shinywidgets[bqplot]'` |
| `@render_drawdata` | `pip install 'shinywidgets[drawdata]'` |
| `@render_geolibre` | `pip install 'shinywidgets[geolibre]'` (Python ≥ 3.11) |
| `@render_holoviews` | `pip install 'shinywidgets[holoviews]'` |
| `@render_ipyaladin` | `pip install 'shinywidgets[ipyaladin]'` |
| `@render_ipycanvas` | `pip install 'shinywidgets[ipycanvas]'` |
| `@render_ipycytoscape` | `pip install 'shinywidgets[ipycytoscape]'` |
| `@render_ipydatagrid` | `pip install 'shinywidgets[ipydatagrid]'` |
| `@render_ipyfilechooser` | `pip install 'shinywidgets[ipyfilechooser]'` |
| `@render_ipyleaflet` | `pip install 'shinywidgets[ipyleaflet]'` |
| `@render_ipysigma` | `pip install 'shinywidgets[ipysigma]'` |
| `@render_ipyvolume` | `pip install 'shinywidgets[ipyvolume]'` |
| `@render_itables` | `pip install 'shinywidgets[itables]'` |
| `@render_jscatter` | `pip install 'shinywidgets[jscatter]'` |
| `@render_k3d` | `pip install 'shinywidgets[k3d]'` |
| `@render_keplergl` | `pip install 'shinywidgets[keplergl]'` |
| `@render_leafmap` | `pip install 'shinywidgets[leafmap]'` |
| `@render_lonboard` | `pip install 'shinywidgets[lonboard]'` (Python < 3.15) |
| `@render_maplibre` | `pip install 'shinywidgets[maplibre]'` |
| `@render_matplotlib` | `pip install 'shinywidgets[matplotlib]'` |
| `@render_mols2grid` | `pip install 'shinywidgets[mols2grid]'` |
| `@render_nglview` | `pip install 'shinywidgets[nglview]'` |
| `@render_mosaic_widget` | `pip install 'shinywidgets[mosaic_widget]'` |
| `@render_niivue` | `pip install 'shinywidgets[niivue]'` |
| `@render_obsplot` | `pip install 'shinywidgets[obsplot]'` |
| `@render_panel` | `pip install 'shinywidgets[panel]'` |
| `@render_perspective` | `pip install 'shinywidgets[perspective]'` |
| `@render_plotly` | `pip install 'shinywidgets[plotly]'` |
| `@render_plotnine` | `pip install 'shinywidgets[plotnine]'` |
| `@render_pygwalker` | `pip install 'shinywidgets[pygwalker]'` |
| `@render_pythreejs` | `pip install 'shinywidgets[pythreejs]'` |
| `@render_pyvista` | `pip install 'shinywidgets[pyvista]'` (Python < 3.15) |
| `@render_quak` | `pip install 'shinywidgets[quak]'` |
| `@render_vizarr` | `pip install 'shinywidgets[vizarr]'` |
| `@render_rerun` | `pip install 'shinywidgets[rerun]'` (Python >= 3.11) |

<<<<<<< HEAD
=======
## Reacting to widgets

Some renderers have *accessors*: methods on the output that read what the user
did, the way `input.foo()` reads an input. Call them in a reactive context;
each returns `None` until the interaction happens (wrap in `req()` to wait for
it).

```python
import plotly.express as px
from shiny import req
from shiny.express import render
from shinywidgets import render_plotly

@render_plotly
def plot():
    # custom_data ties each point back to a row of df
    return px.scatter(df, x="x", y="y", custom_data=[df.index])

@render.data_frame
def picked():
    return plot.selected_rows(df)  # empty until the user selects
```

| Renderer | Accessors |
| --- | --- |
| `@render_plotly` | `clicked()`, `selected()`, `selecting()`, `brushed()`, `brushing()`, `relayout()`, `selected_rows(df)` |
| `@render_altair` | `selected(name)`, `selected_rows(name)` |
| `@render_bokeh` | `selected()`, `selected_rows()`, `tapped()`, `zoomed()` |
| `@render_mols2grid` | `selection()`, `clicked()` |

Streaming selections (plotly's `selecting()` and `brushing()`, altair's
`selected()`, bokeh's `selected()`) are debounced by 250 ms. Change that per
output with `rate_policy` (`"debounce"` or `"throttle"`) and `rate_delay`
(milliseconds, `0` to disable), e.g. `@render_plotly(rate_delay=0)`.

For anything else, read a widget trait reactively with
`reactive_read(output.widget, "trait")`. The same `rate_policy` and
`rate_delay` arguments rate-limit `reactive_read()` on that output's widget,
which helps with chatty traits such as a map's `center`.

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
