import json

from geolibre import Map
from shiny import reactive, render
from shiny.express import input, ui

from shinywidgets import reactive_read, render_geolibre

ui.page_opts(title="GeoLibre demo", fillable=True)

CITIES = {
    "New York": (-74.0, 40.7),
    "San Francisco": (-122.4, 37.8),
    "Chicago": (-87.6, 41.9),
}

with ui.sidebar():
    ui.input_select("city", "Jump to a city", list(CITIES))

# The last map click, as a reactive value (set from geolibre's on_click event)
clicked = reactive.value(None)


@render_geolibre
def glmap():
    m = Map(center=(-98.5, 39.8), zoom=4, layout="embed")
    m.add_geojson(
        "https://raw.githubusercontent.com/PublicaMundi/MappingAPI/master/data/geojson/us-states.json",
        name="US States",
    )
    m.on_click(lambda e: clicked.set(e))
    return m


# When the city selection changes, recenter the map in place
@reactive.effect
def _():
    lng, lat = CITIES[input.city()]
    glmap.widget.set_center(lng, lat, zoom=9)


with ui.card():
    ui.card_header("Last click")
    @render.code
    async def click_info():
        e = clicked()
        return "Click the map" if e is None else json.dumps(e["lngLat"])


with ui.card():
    ui.card_header("Map view (from the synced project)")
    @render.code
    async def view_info():
        project = reactive_read(glmap.widget, "project")
        view = project.get("mapView", {})
        return json.dumps(
            {
                "center": view.get("center"),
                "zoom": round(view.get("zoom", 0), 2),
                "layers": [lyr.get("name") for lyr in project.get("layers", [])],
            }
        )
