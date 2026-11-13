import pandas as pd
from keplergl import KeplerGl
from shiny.express import ui
from shinywidgets import render_keplergl

# A full year (2015) of daily positions for ten tracked bird species migrating
# between South America and the Arctic (vega-datasets' "bird-migration", also
# one of kepler.gl's own demo datasets). kepler.gl needs a real timestamp dtype
# (not a date string) to offer a time filter.
birds = pd.read_csv("https://cdn.jsdelivr.net/gh/vega/vega-datasets@5448e25297c8f705be78e879d5423d55d04dc6f1/data/bird-migration.csv")
birds["date"] = pd.to_datetime(birds["date"])

# A timeRange filter adds the histogram + play button at the bottom of the
# map. The initial window (in epoch milliseconds) spotlights one week in
# April, mid-way through the northward spring migration.
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

ui.page_opts(title="Time filter and playback", fillable=True)


@render_keplergl
def map():
    return KeplerGl(data={"data": birds}, config=CONFIG)
