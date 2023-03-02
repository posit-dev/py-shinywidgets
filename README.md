shinywidgets
================

Render [ipywidgets](https://ipywidgets.readthedocs.io/en/stable/) inside a
[Shiny](https://shiny.rstudio.com/py) app.

## Installation

```sh
pip install shinywidgets
```

## Overview

Every Shiny app has two main parts: the user interface (UI) and server logic.
`{shinywidgets}` provides `output_widget()` for defining where to place a widget in the UI
and `register_widget()` (or `@render_widget`) for supplying a widget-like object to
the `output_widget()` container. More technically, widget-like means:

* Any object that subclasses `{ipywidgets}`'s `Widget` class.
* Some other widget-like object that can be coerced into a `Widget`. Currently, we
  support objects from `{altair}`, `{bokeh}`, and `{pydeck}`, but [please let us
  know](https://github.com/rstudio/py-shinywidgets/issues/new) about other packages that we
  should support.

The recommended way to incorporate `{shinywidgets}` widgets into Shiny apps is to:

1. Initialize and `register_widget()` _once_ for each widget.
    * In most cases, initialization should happen when the user session starts (i.e.,
      the `server` function first executes), but if the widget is slow to initialize and
      doesn't need to be shown right away, you may want to delay that initialization
      until it's needed.
2. Use Shiny's `@reactive.Effect` to reactively modify the widget whenever relevant
   reactive values change.
3. Use `{shinywidgets}`'s `reactive_read()` to update other outputs whenever the widget changes.
    * This way, relevant output(s) invalidate (i.e., recalculate) whenever the relevant
      widget attributes change (client-side or server-side).

The following app below uses `{ipyleaflet}` to demonstrate all these concepts:

```py
from shiny import *
from shinywidgets import output_widget, register_widget, reactive_read
import ipyleaflet as L

app_ui = ui.page_fluid(
    ui.input_slider("zoom", "Map zoom level", value=4, min=1, max=10),
    output_widget("map"),
    ui.output_text("map_bounds"),
)

def server(input, output, session):

    # Initialize and display when the session starts (1)
    map = L.Map(center=(52, 360), zoom=4)
    register_widget("map", map)

    # When the slider changes, update the map's zoom attribute (2)
    @reactive.Effect
    def _():
        map.zoom = input.zoom()

    # When zooming directly on the map, update the slider's value (2 and 3)
    @reactive.Effect
    def _():
        ui.update_slider("zoom", value=reactive_read(map, "zoom"))

    # Everytime the map's bounds change, update the output message (3)
    @output
    @render.text
    def map_bounds():
        b = reactive_read(map, "bounds")
        lat = [b[0][0], b[0][1]]
        lon = [b[1][0], b[1][1]]
        return f"The current latitude is {lat} and longitude is {lon}"

app = App(app_ui, server)
```

<div align="center">
    <img src="https://user-images.githubusercontent.com/1365941/171508416-1ebe157c-b305-4517-9c89-14891dff8f79.gif" width="70%">
</div>

The style of programming above (display and mutate) is great for efficiently performing
partial updates to a widget. This is really useful when a widget needs to display lots
of data and also quickly handle partial updates; for example, toggling the visibility of
a fitted line on a scatterplot with lots of points:

```py
from shiny import *
from shinywidgets import output_widget, register_widget
import plotly.graph_objs as go
import numpy as np
from sklearn.linear_model import LinearRegression

# Generate some data and fit a linear regression
n = 10000
d = np.random.RandomState(0).multivariate_normal([0, 0], [(1, 0.5), (0.5, 1)], n).T
fit = LinearRegression().fit(d[0].reshape(-1, 1), d[1])
xgrid = np.linspace(start=min(d[0]), stop=max(d[0]), num=30)

app_ui = ui.page_fluid(
    output_widget("scatterplot"),
    ui.input_checkbox("show_fit", "Show fitted line", value=True),
)

def server(input, output, session):

    scatterplot = go.FigureWidget(
        data=[
            go.Scattergl(
                x=d[0],
                y=d[1],
                mode="markers",
                marker=dict(color="rgba(0, 0, 0, 0.05)", size=5),
            ),
            go.Scattergl(
                x=xgrid,
                y=fit.intercept_ + fit.coef_[0] * xgrid,
                mode="lines",
                line=dict(color="red", width=2),
            ),
        ]
    )

    register_widget("scatterplot", scatterplot)

    @reactive.Effect
    def _():
        scatterplot.data[1].visible = input.show_fit()

app = App(app_ui, server)
```

<div align="center">
    <img src="https://user-images.githubusercontent.com/1365941/171507230-4b32ce4a-6e80-43a4-9c71-6a1f3ffe443e.gif" width="70%">
</div>


That being said, in a situation where:

* Performant updates aren't important
* Other outputs don't depend on the widget's state
* It's convenient to initialize a widget in a reactive context

Then it's ok to reach for `@render_widget()` (instead of `register_widget()`) which
creates a reactive context (similar to Shiny's `@render_plot()`, `@render_text()`, etc.)
where each time that context gets invalidated, the output gets redrawn from scratch. In
a simple case like the one below, that redrawing may not be noticable, but if you we're
to redraw the entire scatterplot above everytime the fitted line was toggled, there'd
be noticeable delay.

```py
from shiny import *
from shinywidgets import output_widget, render_widget
import ipyleaflet as L

app_ui = ui.page_fluid(
    ui.input_slider("zoom", "Map zoom level", value=4, min=1, max=10),
    output_widget("map")
)

def server(input, output, session):
    @output
    @render_widget
    def map():
        return L.Map(center=(52, 360), zoom=input.zoom())

app = App(app_ui, server)
```

## Frequently asked questions

### How do I size the widget?

`{ipywidgets}`' `Widget` class has [it's own API for setting inline CSS
styles](https://ipywidgets.readthedocs.io/en/stable/examples/Widget%20Styling.html),
including `height` and `width`. So, given a `Widget` instance `w`, you should be able to
do something like:

```py
w.layout.height = "600px"
w.layout.width = "80%"
```

### How do I hide/show a widget?

As mentioned above, a `Widget` class should have a `layout` attribute, which can be
used to set all sorts of CSS styles, including display and visibility. So, if you wanted
to hide a widget and still have space allocated for it:

```py
w.layout.visibility = "hidden"
```

Or, to not give it any space:

```py
w.layout.display = "none"
```

### Can I render widgets that contain other widgets?

Yes! In fact this a crucial aspect to how packages like `{ipyleaflet}` work. In
`{ipyleaflet}`'s case, each [individual marker is a widget](https://ipyleaflet.readthedocs.io/en/latest/layers/circle_marker.html) which gets attached to a `Map()` via `.add_layer()`.

### Does `{shinywidgets}` work with Shinylive?

Shinylive allows some Shiny apps to be statically served (i.e., run entirely in the
browser). [py-shinylive](https://github.com/rstudio/py-shinylive) does have some special
support for `{shinywidgets}` and it's dependencies, which should make most widgets work
out-of-the-box.

In some cases, the package(s) that you want to use may not come pre-bundled with
`{shinywidgets}`; and in that case, you can [include a `requirements.txt`
file](https://shinylive.io/py/examples/#extra-packages) to pre-install those other
packages

## Troubleshooting

If after [installing](#installation) `{shinywidgets}`, you have trouble rendering widgets,
first try running the "hello world" ipywidgets [example](https://github.com/rstudio/py-shinywidgets/blob/main/examples/ipywidgets/app.py). If that doesn't work, it could be that you have an unsupported version
of a dependency like `{ipywidgets}` or `{shiny}`.

If you can run the "hello world" example, but "3rd party" widget(s) don't work, first
check that the extension is properly configured with `jupyter nbextension list`. Even if
the extension is properly configured, it still may not work right away, especially if
that widget requires initialization code in a notebook environment. In this case,
`{shinywidgets}` probably won't work without providing the equivalent setup information to
Shiny. Some known cases of this are:

#### bokeh

To use `{bokeh}` in notebook, you have to run `bokeh.io.output_notebook()`. The
equivalent thing in Shiny is to include the following in the UI definition:

```py
from bokeh.resources import Resources
head_content(HTML(Resources(mode="inline").render()))
```
#### Other widgets?

Know of another widget that requires initialization code? [Please let us know about
it](https://github.com/rstudio/py-shinywidgets/issues/new)!

## Development

If you want to do development on `{shinywidgets}`, run:

```sh
pip install -e ".[dev,test]"
cd js && yarn watch
```
