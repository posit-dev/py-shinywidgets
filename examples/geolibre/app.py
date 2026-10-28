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


# geolibre's command methods send a command to the app and wait for its
# reply. The *_async() variants (added in a geolibre release after 3.5.2;
# https://github.com/opengeos/GeoLibre/issues/3273) await that reply, so --
# like set_center() above, and unlike the blocking fly_to() -- they can run
# directly on Shiny's event loop inside an extended_task. On geolibre 3.5.2
# the blocking fly_to() must instead wait on a worker thread (the wait would
# otherwise block the loop that delivers the reply). See README.md.
@extended_task
async def fly_to_city():
    lng, lat = CITIES[input.city()]
    if hasattr(glmap.widget, "fly_to_async"):
        await glmap.widget.fly_to_async(lng, lat, zoom=9)
    else:
        loop = asyncio.get_running_loop()
        await loop.run_in_executor(None, glmap.widget.fly_to, lng, lat, zoom=9)


@reactive.effect
@reactive.event(input.fly)
def _():
    fly_to_city.invoke()


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
