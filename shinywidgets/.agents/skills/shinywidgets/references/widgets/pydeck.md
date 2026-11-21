# pydeck (`render_pydeck`, deprecated)

## Overview

`render_pydeck` is **deprecated** — do not use it in new code. pydeck
v0.9 removed its Jupyter widget entirely (`Deck.show()` now returns static
HTML; `Deck.update()` raises), so no ipywidgets bridge can render a live
`pydeck.Deck` anymore. With pydeck v0.9+, `render_pydeck` raises a
`TypeError` pointing at the alternatives below.

## Migration

Bring `pydeck.Layer` objects to [`render_maplibre`](maplibre.md)'s
`add_deck_layers()`:

```python
import pydeck as pdk
from maplibre import Map, MapOptions
from maplibre.basemaps import Carto
from shiny import reactive
from shiny.express import input, ui
from shinywidgets import render_maplibre

ui.input_slider("radius", "Hexagon radius (m)", 1000, 10000, 4000, step=500)

POINTS = [[-0.13, 51.51], [-0.12, 51.50], [-2.24, 53.48]]  # [lng, lat]


@render_maplibre
def deck():
    m = Map(MapOptions(style=Carto.DARK_MATTER, center=(-1.9, 52.25), zoom=6))
    m.add_deck_layers([])
    return m


@reactive.effect
def _restyle():
    deck.widget.set_deck_layers(
        [
            pdk.Layer(
                "HexagonLayer",
                POINTS,
                id="hex",
                get_position="-",
                radius=input.radius(),
                extruded=True,
            )
        ]
    )
```

`.widget.set_deck_layers()` restyles in place (the camera stays where the
user left it); read state with `reactive_read(deck.widget, "view_state")`
or `"clicked"`.

Other options:

- **Large data**: [`render_lonboard`](lonboard.md) sends binary
  data once and restyles layers without re-sending it.
- **Static maps only, no interaction needed back to Python**: `@render.ui`
  returning `deck.show()` (a 500px-tall iframe) or
  `ui.tags.iframe(srcdoc=deck.to_html(as_string=True), style="border:0;width:100%;height:100%;flex:1 1 auto")`
  to fill the container. Every change re-sends the whole page and resets
  the camera. Don't return `deck.to_html()` directly — without a filename
  it returns `None`.

**More:** <https://shinywidgets.org/widgets/pydeck/>
