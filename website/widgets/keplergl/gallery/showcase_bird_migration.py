# A year of bird migration in the Americas: a time-scrubbable map
# A 3D hexbin density layer plus kepler.gl's time filter and playback,
# driving a live Shiny detail table of what's in the current time window.
# A species filter updates the map in place, and the camera can be saved and
# restored without losing layer styling or the current time window.
# bucket: showcase
# run: uv run shiny run gallery/showcase_bird_migration.py
# data: vega-datasets "bird-migration.csv" (daily 2015 positions of ten
# tracked species; also one of kepler.gl's own demo datasets)

import copy

import pandas as pd
from keplergl import KeplerGl
from shiny import reactive
from shiny.express import input, render, ui
from shinywidgets import render_keplergl

birds = pd.read_csv("https://cdn.jsdelivr.net/gh/vega/vega-datasets@5448e25297c8f705be78e879d5423d55d04dc6f1/data/bird-migration.csv")
birds["date"] = pd.to_datetime(birds["date"])
SPECIES = sorted(birds["species"].unique())

DEFAULT_CONFIG = {
    "version": "v1",
    "config": {
        "visState": {
            "layers": [
                {
                    "id": "birds-hex",
                    "type": "hexagon",
                    "config": {
                        "dataId": "data",
                        "label": "Birds (density)",
                        "columns": {"lat": "lat", "lng": "lon"},
                        "isVisible": True,
                        "visConfig": {
                            "worldUnitSize": 100,
                            "resolution": 8,
                            "colorRange": {
                                "name": "Global Warming",
                                "type": "sequential",
                                "category": "Uber",
                                "colors": [
                                    "#4C0035", "#880030", "#B72F15",
                                    "#D6610A", "#EF9100", "#FFC300",
                                ],
                            },
                            "coverage": 0.9,
                            "elevationScale": 40,
                            "enable3d": True,
                        },
                    },
                    "visualChannels": {
                        "colorField": None,
                        "colorScale": "quantile",
                        "sizeField": None,
                        "sizeScale": "linear",
                    },
                }
            ],
            "filters": [
                {
                    "dataId": ["data"],
                    "id": "migration-date-window",
                    "name": ["date"],
                    "type": "timeRange",
                    "value": [1_427_846_400_000, 1_429_056_000_000],
                    "plotType": {"type": "histogram", "interval": "1-day"},
                    "animationWindow": "free",
                    "view": "enlarged",
                    "speed": 0.5,
                    "enabled": True,
                }
            ],
        },
        "mapState": {
            "latitude": 8.0,
            "longitude": -82.0,
            "zoom": 2.1,
            "pitch": 45,
            "bearing": -10,
        },
    },
}

saved_config = reactive.value(None)

ui.page_opts(title="A year of bird migration in the Americas", fillable=True)

with ui.layout_columns(col_widths=[8, 4]):
    with ui.card(full_screen=True):

        @render_keplergl(rate_policy="throttle", rate_delay=0.5)
        def map():
            with reactive.isolate():
                return KeplerGl(data={"data": filtered()}, config=DEFAULT_CONFIG)

    with ui.div():
        with ui.card():
            ui.card_header("Filter by species")
            ui.input_checkbox_group(
                "species", None, choices=SPECIES, selected=SPECIES
            )
            ui.input_action_button("save", "Save current view", class_="mt-2")
            ui.input_action_button("restore", "Restore saved view", class_="mt-1")

        with ui.card(full_screen=True):
            ui.card_header("Birds in the current time window")

            @render.data_frame
            def visible_rows():
                config = map.read("config")
                filters = config.get("config", {}).get("visState", {}).get("filters", [])
                if not filters:
                    return birds.iloc[0:0]
                start_ms, end_ms = filters[0]["value"]
                start = pd.to_datetime(start_ms, unit="ms")
                end = pd.to_datetime(end_ms, unit="ms")
                window = filtered()[filtered()["date"].between(start, end)]
                return render.DataGrid(
                    window[["species", "date", "lat", "lon"]],
                    height="100%",
                )


def filtered():
    kept = input.species() or SPECIES
    return birds[birds["species"].isin(kept)]


@reactive.effect
@reactive.event(input.species)
def _():
    # In place: the hexbin layer, time filter, and camera all survive.
    map.widget.data = {"data": filtered()}


@reactive.effect
@reactive.event(input.save)
def _():
    saved_config.set(map.read("config"))


@reactive.effect
@reactive.event(input.restore)
def _():
    saved = saved_config.get()
    if saved is None:
        return
    # Camera-only restore: stripping `visState.layers` keeps the current layer
    # and time window intact -- a config-set *with* an explicit layer breaks
    # rendering on keplergl 0.4.0, and incoming filter values are ignored
    # anyway (see the guide's "Gotchas and limitations").
    restored = copy.deepcopy(saved)
    restored.get("config", {}).get("visState", {}).pop("layers", None)
    map.widget.config = restored
