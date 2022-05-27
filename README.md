ipyshiny
================

Render [ipywidgets](https://ipywidgets.readthedocs.io/en/stable/) inside a [Shiny](https://pyshiny.netlify.app/) app.

## Getting started

### Installation

```sh
pip install ipyshiny --extra-index-url=https://pyshiny.netlify.app/pypi
```

### Examples

TODO: deploy `examples/` folder to Connect/pyodide and link to them here.

### Quick start

Every Shiny app has two fundamental pieces: the user interface (UI) and server logic. `{ipyshiny}`
provides `output_widget()` for placing a widget's UI container and
`display_widget()` for passing a widget-like object to that container. More technically, this includes:

* Any object that subclasses `{ipywidgets}`'s `Widget` class.
* Some other widget-like object that can be coerced into a `Widget`. Currently, we support objects from `{altair}`, `{bokeh}`, and `{pydeck}`, but [please let us know](https://github.com/rstudio/ipyshiny/issues/new) about other packages that we should support.

Due to the nature of how `Widget`s are designed, when used with Shiny, they must be initialized inside of the `server` function, like below:

```py
from shiny import *
from ipyshiny import output_widget, display_widget
import ipyleaflet as L

app_ui = ui.page_fluid(
    output_widget("map")
)

def server(input, output, session):
    map = L.Map(center=(52, 360), zoom=4)
    display_widget("map", map)

app = App(app_ui, server)
```

#### Using as a reactive view

One of the neat things about `{ipywidgets}`' `Widget` design is that any modification of
a widget's server-side state immediately propogates to the client-side state/view. Let's
leverage that behavior to reactively update the map's zoom level everytime an
`input_slider()` changes (TODO: link to Shiny's reactivity article).

```py
from shiny import *
from ipyshiny import output_widget, display_widget
import ipyleaflet as L

app_ui = ui.page_fluid(
    ui.input_slider("zoom", "Set zoom level", value=4, min=1, max=10),
    output_widget("map")
)

def server(input, output, session):
    map = L.Map(center=(52, 360))
    display_widget("map", map)

    @reactive.Effect()
    def _():
        map.zoom = input.zoom()

app = App(app_ui, server)
```

TODO: Compare this to @interact() and mention two main benefits:
* Effect can be invalidated by other reactive values
* input_slider() updates are debounced whereas @interact() continuously updates


It's not considered best practice, but sometimes it is convenient to initialize a
widget _within a reactive context_, which can be done `@render_widget()`:

```py
from shiny import *
from ipyshiny import output_widget, display_widget
import ipyleaflet as L

app_ui = ui.page_fluid(
    ui.input_slider("zoom", "Set zoom level", value=4, min=1, max=10),
    output_widget("map")
)

def server(input, output, session):
    @output(name="map")
    @render_widget()
    def _():
      return L.Map(center=(52, 360), zoom=input.zoom())

app = App(app_ui, server)
```

For seasoned Shiny users, `@render_widget()` provides a more natural way to pass
reactive values to the constructor of a widget, but it does come with a downside in that
everytime the widget updates, it gets recreated and redrawn from scratch. If this update
is computationally inexpensive (as it is in the example above), this difference won't
really matter. However, if your widgets are feeling very responsive, you likely
want to switch from `@render_widget()` to `display_widget()`.

TODO: an example of adding removing a single marker?

#### Using as a reactive controller

The previous section outlined how a typical Shiny input (e.g., `input_slider()`) can be
used to update/control a widget. We can also use the widget's state like an input
controller of some other view. To make this sort of thing easy, `{ipyshiny}` provides
`reactive_read()` to read widget attribute(s) as though they are reactive value(s) (i.e.,
when the attributes change, they invalidate the context in which they are read):


```py
from shiny import *
from ipyshiny import output_widget, display_widget, reactive_read
import ipyleaflet as L

app_ui = ui.page_fluid(
    ui.input_slider("zoom", "Set zoom level", value=4, min=1, max=10),
    output_widget("map"),
    ui.output_text_verbatim("map_bounds")
)

def server(input, output, session):
    map = L.Map(center=(52, 360))
    display_widget("map", map)

    @reactive.Effect()
    def _():
        map.zoom = input.zoom()

    @output(name="map_bounds")
    def _():
      return reactive_read(map, "bounds")

app = App(app_ui, server)
```




## Troubleshooting {#troubleshooting}

### The widget doesn't render at all

There's at least a few different reasons why a widget may not render at all in `{ipyshiny}`

### Widgets that require initialization code

A number of `{ipywidgets}` packages require you to run some initialization code in order to use
them in Jupyter. In this case, `{ipyshiny}` probably won't work without providing equivalent information to Shiny. Some known cases of this are:

#### bokeh

TODO: Provide initialization code

#### itables

TODO: Provide initialization code

#### Other widgets

Know of another widget that requires initialization code? [Please let us know about it](https://github.com/rstudio/ipyshiny/issues/new)!





## Development

If you want to do development, run:

```sh
pip install -e .
cd js && yarn watch
```

Additionally, you can install pre-commit hooks which will automatically reformat and lint the code when you make a commit:

```sh
pre-commit install

# To disable:
# pre-commit uninstall
```
