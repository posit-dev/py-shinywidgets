import pandas as pd
from keplergl import KeplerGl
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

ui.page_opts(title="Time window drives a detail table", fillable=True)

with ui.layout_columns(col_widths=[7, 5]):
    with ui.card(full_screen=True):

        @render_keplergl(rate_policy="throttle", rate_delay=0.5)
        def map():
            return KeplerGl(data={"data": birds}, config=CONFIG)

    with ui.card(full_screen=True):
        ui.card_header("Birds in the current time window")

        @render.data_frame
        def visible_rows():
            config = map.read("config")
            filters = config.get("config", {}).get("visState", {}).get("filters", [])
            if not filters:
                return birds.iloc[0:0]
            start_ms, end_ms = filters[0]["value"]
            start, end = pd.to_datetime(start_ms, unit="ms"), pd.to_datetime(end_ms, unit="ms")
            window = birds[birds["date"].between(start, end)]
            return render.DataGrid(
                window[["species", "date", "lat", "lon"]],
                height="100%",
            )
