# kepler.gl station explorer
# A small, adaptable starting point: a slider filters a point dataset, the
# map updates in place (camera and any side-panel styling survive), and a
# .read("config") on the map reports the current view.
# bucket: template
# run: uv run shiny run gallery/template_station_explorer.py
# data: plotly.express.data.carshare() (Montreal car-share station activity)

import plotly.express as px
from shiny import reactive
from shiny.express import input, render, ui
from shinywidgets import render_keplergl

carshare = px.data.carshare().rename(
    columns={"centroid_lat": "lat", "centroid_lon": "lon"}
)

ui.page_opts(title="Car-share station explorer", fillable=True)

with ui.sidebar():
    ui.input_slider("min_hours", "Minimum car-share hours", 0, 3000, 0, step=100)

    @render.code
    def view_state():
        config = map.read("config")
        state = config.get("config", {}).get("mapState", {})
        if not state:
            return "Waiting for the map to load..."
        return f"zoom: {state['zoom']:.2f}"


def filtered():
    return carshare[carshare["car_hours"] >= input.min_hours()]


@render_keplergl
def map():
    with reactive.isolate():
        return filtered()


@reactive.effect
@reactive.event(input.min_hours)
def _():
    map.widget.data = {"data": filtered()}
