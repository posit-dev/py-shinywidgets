import leafmap
from shiny import reactive, req
from shiny.express import input, ui
from shinywidgets import render_leafmap

CITIES = {
    "Seattle": (47.6062, -122.3321),
    "Portland": (45.5152, -122.6784),
    "Vancouver": (49.2827, -123.1207),
}

ui.page_opts(title="Updating leafmap in place", fillable=True)

with ui.sidebar():
    ui.input_select("city", "Fly to", list(CITIES))
    ui.input_slider("opacity", "Basemap opacity", 0, 1, value=1, step=0.1)


@render_leafmap
def map():
    m = leafmap.Map(center=(47.6, -122.33), zoom=9)
    m.add_basemap("Esri.WorldImagery", show=True)
    return m


# Re-rendering here would rebuild the whole map (new JS widget, reset zoom and
# any user edits); setting traits on the live .widget instead keeps the
# camera, drawn shapes, and everything else the user already has on screen
@reactive.effect
def _fly_to():
    m = map.widget
    req(m)
    lat, lng = CITIES[input.city()]
    m.center = (lat, lng)
    m.zoom = 11


@reactive.effect
def _set_opacity():
    m = map.widget
    req(m)
    m.layers[-1].opacity = input.opacity()
