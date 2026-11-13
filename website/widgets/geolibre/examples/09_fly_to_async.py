from __future__ import annotations

import asyncio
import json

from geolibre import Map
from shiny import reactive, render
from shiny.express import input, ui
from shiny.reactive import extended_task

from shinywidgets import render_geolibre

ui.page_opts(title="fly_to_async()", fillable=True)

CITIES = {
    "New York": (-74.0, 40.7),
    "San Francisco": (-122.4, 37.8),
    "Chicago": (-87.6, 41.9),
}

with ui.sidebar():
    ui.input_select("city", "Fly to a city", list(CITIES))
    ui.input_action_button("fly", "Fly there (animated)")

with ui.card(full_screen=True):

    @render_geolibre
    def map():
        return Map(center=(-98.5, 39.8), zoom=4)


# fly_to_async() awaits the app's reply instead of blocking a thread for it,
# so it runs directly on Shiny's event loop -- but only from inside an
# extended_task: awaiting it from a plain reactive.effect deadlocks, because
# the reply can't be delivered until that effect finishes. An extended_task
# can't read reactive sources itself (input.city() would raise) -- read it
# before invoking, and pass it in as an argument.
@extended_task
async def fly_to_city(lng: float, lat: float):
    await map.widget.fly_to_async(lng, lat, zoom=9, duration=800)
    await asyncio.sleep(1)  # let the animation finish before querying the camera
    return await map.widget.get_center_async()


@reactive.effect
@reactive.event(input.fly)
def _():
    fly_to_city.invoke(*CITIES[input.city()])


@render.code
def landed():
    status = fly_to_city.status()
    if status == "error":
        return f"error: {fly_to_city.error()}"
    if status != "success":
        return "none"
    return json.dumps([round(c, 2) for c in fly_to_city.result()])
