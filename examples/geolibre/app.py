import asyncio
import json

from geolibre import Map
from shiny import reactive, render
from shiny.express import input, ui
from shiny.reactive import extended_task

from shinywidgets import reactive_read, render_geolibre

ui.page_opts(title="GeoLibre demo", fillable=True)

CITIES = {
    "New York": (-74.0, 40.7),
    "San Francisco": (-122.4, 37.8),
    "Chicago": (-87.6, 41.9),
}

with ui.sidebar():
    ui.input_select("city", "Jump to a city", list(CITIES))
    ui.input_action_button("fly", "Fly there (animated)")

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


# fly_to() blocks waiting for a reply from the app, so -- unlike set_center()
# above -- it can never run on Shiny's event-loop thread (the wait would
# block the loop that delivers the reply). Run it on a worker thread inside
# an extended_task (geolibre >= 3.5.2 polls for the reply instead of pumping
# a Jupyter kernel; see README.md).
@extended_task
async def fly_to_city(city):
    lng, lat = CITIES[city]
    loop = asyncio.get_running_loop()
    await loop.run_in_executor(None, glmap.widget.fly_to, lng, lat, zoom=9)


@reactive.effect
@reactive.event(input.fly)
def _():
    # Read inputs here, not inside fly_to_city(): an @extended_task body runs
    # outside a reactive context, where reading input.city() errors.
    fly_to_city.invoke(input.city())


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
