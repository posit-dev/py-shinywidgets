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
| `@render_quak` | `pip install 'shinywidgets[quak]'` |
| `@render_vizarr` | `pip install 'shinywidgets[vizarr]'` |
| `@render_rerun` | `pip install 'shinywidgets[rerun]'` (Python >= 3.11) |

## Reacting to user interaction

When a user clicks, selects, or zooms in a plot, your app often needs to react:
show the selected rows, filter another plot, or look up details. For the most
common plotting libraries, the output itself has methods that read these
interactions, much like `input.my_slider()` reads an input. We call them
**accessors**.

```python
import plotly.express as px
from shiny.express import render
from shinywidgets import render_plotly

df = px.data.iris()

@render_plotly
def plot():
    # custom_data ties each point back to its row of df (see "Getting rows")
    fig = px.scatter(df, x="sepal_width", y="sepal_length", custom_data=[df.index])
    fig.update_layout(dragmode="select")
    return fig

@render.data_frame
def picked():
    # Re-runs whenever the user selects points with the box or lasso tool
    return plot.selected_rows(df)
```

### Which accessors exist

| Renderer | Accessor | Returns |
| --- | --- | --- |
| `@render_plotly` | `clicked()` | the clicked points, as a pandas `DataFrame` |
| | `selected()` | the points of a box or lasso selection, once the drag ends |
| | `selecting()` | the same, updated while the user drags |
| | `brushed()` / `brushing()` | the selected *region* (box range or lasso path), at the end of / during the drag |
| | `relayout()` | axis ranges after a zoom, pan, or autoscale |
| | `selected_rows(df, key=None)` | the rows of `df` the user selected |
| `@render_altair` | `selected(name=None)` | the current state of a named selection (altair's `IntervalSelection`, `PointSelection`, or `IndexSelection`) |
| | `selected_rows(name=None, df=None)` | the rows of the chart's data in that selection |
| `@render_bokeh` | `selected()` | the selected row indices of the plot's `ColumnDataSource` |
| | `selected_rows()` | those rows, as a pandas `DataFrame` |
| | `tapped()` | the most recent tap (`bokeh.events.Tap`, with `.x` and `.y` in data units) |
| | `zoomed()` | the plot's ranges after a zoom or pan (`bokeh.events.RangesUpdate`) |

Each method's docstring has the details (columns, coordinate spaces, defaults).
For other widgets, see [Reading any widget state](#reading-any-widget-state).

### How accessors behave

**Read them like inputs.** Call an accessor inside a reactive function (a
`@render.*` function, `@reactive.calc`, or `@reactive.effect`), and that function
re-runs whenever the interaction changes.

**`None` means "hasn't happened yet".** Until the user clicks, `plot.clicked()`
returns `None`. That is a normal state, not an error, so check for it, or use
`req()` to wait for the interaction:

```python
from shiny import req

@render.text
def info():
    pts = req(plot.clicked())  # nothing shows until the first click
    return f"You clicked x={pts['x'].iloc[0]}"
```

Altair's `selected()` is the exception: altair reports its selections from the
start, so it returns an *empty* selection rather than `None` until the user
selects something.

**Re-rendering starts over.** When the render function re-runs, for example
because it reads an input, the user gets a new plot, and accessors go back to
`None` (an empty selection for altair). A click on the old plot doesn't describe
the new one.

**Repeating the same interaction doesn't re-fire.** Clicking the same point
twice is not a change, just as setting an input to the value it already has
isn't. Readers re-run only when the result changes.

**Plotly clears like the plot does.** Double-clicking a plotly plot clears
`clicked()`, and a deselect (double-clicking after a box or lasso selection)
clears `selected()`, `selecting()`, `brushed()`, and `brushing()`, back to `None`.

**Don't read an accessor in its own render function.** Something like
`plot.clicked()` inside `def plot()` raises an error. The render function builds
a new plot each time it runs, which resets the accessor. To change a plot in
response to a click, update it in place from an effect instead:

```python
from shiny import reactive, req

@reactive.effect
def _():
    pts = req(plot.clicked())
    plot.widget.layout.title.text = f"Clicked x={pts['x'].iloc[0]}"
```

### Getting rows of your data

The points plotly reports describe the *plot* (trace number, position within
the trace, coordinates), not your data. `selected_rows(df)` maps them back to
rows of `df`. For this to work, each point has to carry its row's identity as
`customdata`:

- **pandas:** `px.scatter(df, ..., custom_data=[df.index])`. Points are matched
  to `df`'s index labels, so this also works after filtering or sorting `df`.
- **polars:** `df = df.with_row_index()`, then `custom_data=["index"]`. Points
  are matched to row positions.
- **Your own key column:** `custom_data=["id"]` with `selected_rows(df, key="id")`
  matches points to the values of the `id` column.

`selected_rows()` returns an empty frame while nothing is selected, so you can
pass it straight to `@render.data_frame`.

Altair's `selected_rows()` needs no setup. It applies the selection to the
chart's own data the way Vega-Lite does, including binned fields (a click on a
histogram bar selects the rows in that bin). It works with pandas and polars
data. If the chart's data is a URL, pass the frame yourself:
`chart.selected_rows("brush", df=my_df)`. Dates are compared the way the browser
showed them, so a time-zone-naive date column is read in the user's time zone.
Always give selections a name (`alt.selection_interval(name="brush")`), since
altair's generated names change between renders.

Bokeh's `selected_rows()` returns rows of the plot's `ColumnDataSource`. It
requires a plot with exactly one data source.

### Rate limiting

Some interactions stream many updates per second while the user drags. By
default, the streaming accessors (plotly's `selecting()` and `brushing()`,
altair's `selected()`, bokeh's `selected()`) are **debounced** by 250 ms: they
update once the user pauses, rather than on every mouse move. Clicks, final
selections, and zooms are never delayed.

To change this, pass these arguments to the render decorator:

- `rate_policy`: `"debounce"` waits until updates pause for `rate_delay`
  milliseconds, then reports the latest. `"throttle"` reports at most once every
  `rate_delay` milliseconds while updates keep coming.
- `rate_delay`: the window in milliseconds (default 250). `0` turns rate
  limiting off, so readers follow every update.

```python
@render_altair(rate_delay=0)  # follow the brush as it moves
def chart():
    ...
```

### Reading any widget state

Every widget output also has `.widget`, the underlying
[ipywidget](https://ipywidgets.readthedocs.io/). Use `reactive_read()` to read
one of its traits reactively; this works for any widget, including those without
accessors:

```python
import ipyleaflet
from shiny.express import render
from shinywidgets import reactive_read, render_widget

@render_widget
def world():
    return ipyleaflet.Map(center=(52, 10), zoom=5)

@render.text
def center():
    return str(reactive_read(world.widget, "center"))
```

`rate_policy` and `rate_delay` also apply to `reactive_read()` on that output's
widget. They are off by default here, so pass them to rate-limit traits that
change quickly, e.g. `@render_widget(rate_policy="throttle")` for a map's
`center` while the user pans.

### Widgets shared across sessions

A widget built inside `shared_lifetime()` is shown to every user. Its accessors
report whichever user interacted with it last.

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
