import ipyleaflet as L
from shiny import reactive
from shiny.express import input, ui
from shinywidgets import render_ipyleaflet

ui.page_opts(title="In-place layer updates", fillable=True)

OUTLINE = {
    "type": "Feature",
    "properties": {},
    "geometry": {
        "type": "Polygon",
        "coordinates": [
            [[-74.00, 40.72], [-73.98, 40.72], [-73.98, 40.74], [-74.00, 40.74], [-74.00, 40.72]]
        ],
    },
}

with ui.sidebar():
    ui.input_checkbox("show_outline", "Show outline", True)
    ui.input_radio_buttons("color", "Outline color", ["blue", "red", "green"])
    ui.input_checkbox("satellite", "Satellite basemap", False)

with ui.card():

    @render_ipyleaflet
    def map():
        m = L.Map(center=(40.73, -73.99), zoom=13)
        m.add(L.GeoJSON(data=OUTLINE, style={"color": "blue", "fillOpacity": 0.1}, name="outline"))
        return m


def outline():
    return next(lyr for lyr in map.widget.layers if lyr.name == "outline")


# Each effect mutates a trait on the already-rendered map, so the browser
# patches the one layer that changed instead of rebuilding the whole map --
# the pan/zoom the user has done is never disturbed.
@reactive.effect
def _toggle_outline():
    outline().visible = input.show_outline()


@reactive.effect
def _restyle_outline():
    outline().style = {**outline().style, "color": input.color()}


@reactive.effect
def _swap_basemap():
    m = map.widget
    old = next(lyr for lyr in m.layers if lyr.base)
    basemap = L.basemaps.Esri.WorldImagery if input.satellite() else L.basemaps.OpenStreetMap.Mapnik
    new = L.basemap_to_tiles(basemap)
    new.base = True
    m.substitute(old, new)
