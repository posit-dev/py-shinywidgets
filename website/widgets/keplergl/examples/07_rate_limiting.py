import pandas as pd
from keplergl import KeplerGl
from shiny import reactive
from shiny.express import render, ui
from shinywidgets import render_keplergl

birds = pd.read_csv("https://cdn.jsdelivr.net/gh/vega/vega-datasets@5448e25297c8f705be78e879d5423d55d04dc6f1/data/bird-migration.csv")
birds["date"] = pd.to_datetime(birds["date"])

CONFIG = {
    "version": "v1",
    "config": {
        "visState": {
            "filters": [
                {
                    "dataId": ["data"],
                    "id": "migration-date-window",
                    "name": ["date"],
                    "type": "timeRange",
                    "value": [1_427_846_400_000, 1_428_451_200_000],
                    "plotType": {"type": "histogram", "interval": "1-day"},
                    "animationWindow": "free",
                    "view": "enlarged",
                    "speed": 1,
                    "enabled": True,
                }
            ],
        },
        "mapState": {
            "latitude": 25.0,
            "longitude": -85.0,
            "zoom": 3.5,
        },
    },
}

ui.page_opts(title="Rate-limiting .read()", fillable=True)

with ui.layout_columns(col_widths=[8, 4]):
    with ui.card(full_screen=True):

        # `config` rewrites on almost every animation frame during playback.
        # Without a rate policy, every frame invalidates every reader.
        @render_keplergl(rate_policy="throttle", rate_delay=0.5)
        def map():
            return KeplerGl(data={"data": birds}, config=CONFIG)

    with ui.card():
        ui.card_header(".read() invocations (throttled to 2/s)")
        count = reactive.value(0)

        @reactive.effect
        def _():
            map.read("config")
            with reactive.isolate():
                count.set(count.get() + 1)

        @render.code
        def n():
            return f"reads so far: {count.get()}"
