# shinywidgets

Render [Jupyter Widgets](https://ipywidgets.readthedocs.io/en/stable/) inside a
[Shiny](https://shiny.posit.co/py/) app.

Much of Python's interactive visualization — plotly, altair, lonboard,
itables, and many more — is built as Jupyter widgets, made for notebooks.
shinywidgets brings those widgets into Shiny, so the charts, maps, and tables
you explored with can become a web app anyone can open, without rebuilding
them with different tools.

- **Your notebook code carries over.** Return the figure, map, or table you'd
  display in a notebook, and shinywidgets handles the rest.
- **What users do becomes an input.** A lasso, a click, an edited cell — each
  widget's interactions are readable from your app like any other Shiny
  input.
- **Updates are fast.** Change the widget that's already on screen instead of
  rebuilding it, so apps stay responsive and users keep their zoom and
  selection.

Dozens of widget libraries have first-class support — charts (plotly, altair,
bokeh, …), maps (lonboard, ipyleaflet, …), tables (itables, perspective, …),
3D, networks, and scientific viewers — and any other ipywidget works with the
generic `@render_widget`. The
[website](https://posit-dev.github.io/py-shinywidgets/) has a guide and
runnable example for each one, plus a gallery of complete apps.

## Example

A whole app, in a few lines. Lasso some countries, and the table updates to
match:

```python
import plotly.express as px
from shiny.express import render, ui
from shinywidgets import render_plotly

df = px.data.gapminder().query("year == 2007").reset_index(drop=True)

with ui.layout_columns():

    @render_plotly
    def plot():
        fig = px.scatter(
            df, x="gdpPercap", y="lifeExp", color="continent",
            hover_name="country", custom_data=[df.index],
        )
        return fig.update_layout(dragmode="lasso")

    @render.data_frame
    def table():
        return plot.selected_rows(df)[["country", "continent", "lifeExp"]]
```

## Installation

```sh
pip install shinywidgets
```

The core doesn't include any widget library. Each library has a matching
*extra* that installs everything its `@render_*` decorator needs, e.g.
`pip install 'shinywidgets[plotly]'`. Every widget's
[guide](https://posit-dev.github.io/py-shinywidgets/) shows its install
command near the top.

## Learn more

- [Why shinywidgets?](https://posit-dev.github.io/py-shinywidgets/guide/why/) —
  the motivation, and how it compares to notebooks, Streamlit, and Dash.
- [Your first widget app](https://posit-dev.github.io/py-shinywidgets/guide/first-app/) —
  a step-by-step walkthrough.
- [Gallery](https://posit-dev.github.io/py-shinywidgets/gallery/) — complete,
  open-source apps.

## Development

If you want to do development on shinywidgets, run:

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
