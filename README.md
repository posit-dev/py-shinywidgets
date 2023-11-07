shinywidgets
================

Render [ipywidgets](https://ipywidgets.readthedocs.io/en/stable/) inside a
[Shiny](https://shiny.rstudio.com/py) app.

## Installation

```sh
pip install shinywidgets
```

## Overview

See the [using ipywidgets section](https://shiny.rstudio.com/py/docs/ipywidgets.html) of the Shiny for Python website.

## Frequently asked questions

### What ipywidgets are supported?

In theory, shinywidgets supports any instance that inherits from `{ipywidgets}`' `Widget` class. That is, if `isinstance(obj, ipywidgets.widgets.Widget)` returns `True` for some object `obj`, then `{shinywidgets}` should be able to render it.

`{shinywidgets}` can also render objects that don't inherit from `Widget`, but have a known way of coercing into a `Widget` instance. This list currently includes:

* Altair charts (i.e., `altair.Chart()` instances).
* Plotly figures (i.e., `plotly.go.Figure()`)
* Pydeck's `Deck` class (via it's `.show()` method).
* Bokeh widgets (via the [jupyter_bokeh](https://github.com/bokeh/jupyter_bokeh) package).
  * Bokeh widgets are a bit of a special case, as they require some extra setup to work in Shiny. See the [Bokeh widgets aren't displaying, what gives?](#bokeh-widgets-arent-displaying-what-gives) section below for more details.

[See here](https://github.com/rstudio/py-shinywidgets/blob/main/shinywidgets/_as_widget.py) for more details on how these objects are coerced into `Widget` instances, and if you know of other packages that should be added to this list, please [let us know](https://github.com/rstudio/py-shinywidgets/issues/new).

### Bokeh setup

Similar to how you have to run `bokeh.io.output_notebook()` to run `{bokeh}` in notebook, you also have to explicitly bring the JS/CSS dependencies to the Shiny app, which can be done this way:

```py
from shiny import ui
from shinywidgets import bokeh_dependencies

app_ui = ui.page_fluid(
    bokeh_dependencies(),
    # ...
)
```


### Does `{shinywidgets}` work with Shinylive?

To some extent, yes. As shown on the official [shinylive examples](https://shinylive.io/py/examples/), packages like plotly and ipyleaflet work (as long as you've provided the proper dependencies in a [`requirements.txt` file](https://shinylive.io/py/examples/#extra-packages)), but other packages like altair and qgrid may not work (at least currently) due to missing wheel files and/or dependencies with compiled code that can't be compiled to WebAssembly.

### How do I size the widget?

`{ipywidgets}`' `Widget` class has [it's own API for setting inline CSS
styles](https://ipywidgets.readthedocs.io/en/stable/examples/Widget%20Styling.html),
including `height` and `width`. So, given a `Widget` instance `w`, you should be able to
do something like:

```py
w.layout.height = "100%"
w.layout.width = "100%"
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


## Development

If you want to do development on `{shinywidgets}`, run:

```sh
pip install -e ".[dev,test]"
cd js && yarn watch
```
