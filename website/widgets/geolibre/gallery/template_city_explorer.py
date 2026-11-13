# GeoLibre city explorer
# A small starting point: jump to a city instantly (set_center, in place) or
# fly there with an animation (fly_to_async, awaited inside an extended_task
# since it can't run on Shiny's event-loop thread directly). Click a marker
# for its population.
# bucket: template
# run: uv run --no-sync shiny run docs/widget-guides/geolibre/gallery/template_city_explorer.py
# data: 8 major US cities, hardcoded (name, lng, lat, population)

from __future__ import annotations

from geolibre import Map
from shiny import reactive, req
from shiny import ui as core_ui
from shiny.express import input, render, ui
from shiny.reactive import extended_task

from shinywidgets import render_geolibre

ui.page_opts(title="GeoLibre city explorer", fillable=True)

CITIES = {
    "New York": (-74.0, 40.7, 8_478_000),
    "Los Angeles": (-118.2, 34.0, 3_878_000),
    "Chicago": (-87.6, 41.9, 2_721_000),
    "Houston": (-95.4, 29.8, 2_314_000),
    "Phoenix": (-112.1, 33.4, 1_650_000),
    "Denver": (-104.99, 39.74, 715_000),
    "Seattle": (-122.33, 47.6, 737_000),
    "Miami": (-80.19, 25.76, 442_000),
}

last_click = reactive.value(None)

with ui.sidebar():
    ui.input_select("city", "Jump to a city", list(CITIES))
    ui.input_action_button("fly", "Fly there (animated)")

with ui.layout_columns(col_widths=[9, 3]):
    with ui.card(full_screen=True):

        @render_geolibre
        def map():
            m = Map(center=(-98.5, 39.8), zoom=3.5)
            layer_id = m.add_circle_markers(
                [(lng, lat) for lng, lat, _ in CITIES.values()],
                name="Cities",
                radius=10,
                fillColor="#e3342f",
            )
            m.set_identify(layer_id)
            m.on_click(lambda e: last_click.set(e))
            return m

    with ui.card():
        ui.card_header("Clicked city")

        @render.ui
        def detail():
            event = req(last_click())
            features = event.get("features") or []
            if not features:
                return "Click a marker"
            lng, lat = features[0]["geometry"]["coordinates"]
            name, (_, _, pop) = min(
                CITIES.items(), key=lambda kv: (kv[1][0] - lng) ** 2 + (kv[1][1] - lat) ** 2
            )
            return core_ui.value_box(name, f"{pop:,} people")


# set_center() mutates the project in place -- instant, no animation
@reactive.effect
def _():
    lng, lat, _ = CITIES[input.city()]
    map.widget.set_center(lng, lat, zoom=9)


# fly_to_async() awaits the app's reply, so it has to run inside an
# extended_task -- awaiting it from a plain reactive.effect deadlocks.
@extended_task
async def fly_to_city(lng: float, lat: float):
    await map.widget.fly_to_async(lng, lat, zoom=9, duration=1000)


@reactive.effect
@reactive.event(input.fly)
def _():
    lng, lat, _ = CITIES[input.city()]
    fly_to_city.invoke(lng, lat)
