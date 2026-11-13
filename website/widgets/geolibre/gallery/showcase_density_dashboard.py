# GeoLibre population-density dashboard
# A fuller app: a styled choropleth with a legend and a configured click
# popup, the built-in Measure tool, a table of the 10 densest states that
# flies the map to a selection, a chart of what's on screen as you pan/zoom,
# and a PNG export of the current view.
# bucket: showcase
# run: uv run --no-sync shiny run docs/widget-guides/geolibre/gallery/showcase_density_dashboard.py
# data: US state boundaries + 2020-census density, from PublicaMundi's public
#       us-states.json (state centroids are approximated from the polygons)

from __future__ import annotations

import pandas as pd
import requests
from geolibre import Map
from matplotlib.figure import Figure
from shiny import reactive, render, req
from shiny.express import ui

from shinywidgets import render_geolibre

ui.page_opts(title="US population density", fillable=True)

US_STATES_URL = (
    "https://raw.githubusercontent.com/PublicaMundi/MappingAPI/"
    "master/data/geojson/us-states.json"
)
STATES_GEOJSON = requests.get(US_STATES_URL, timeout=20).json()


def _centroid(feature) -> tuple[float, float]:
    geom = feature["geometry"]
    ring = geom["coordinates"][0] if geom["type"] == "Polygon" else geom["coordinates"][0][0]
    xs = [pt[0] for pt in ring]
    ys = [pt[1] for pt in ring]
    return sum(xs) / len(xs), sum(ys) / len(ys)


STATES = pd.DataFrame(
    [
        {
            "name": f["properties"]["name"],
            "density": f["properties"]["density"],
            "lng": _centroid(f)[0],
            "lat": _centroid(f)[1],
        }
        for f in STATES_GEOJSON["features"]
    ]
)
DENSEST_10 = STATES.nlargest(10, "density").reset_index(drop=True)

with ui.layout_columns(col_widths=[8, 4], row_heights=[3, 2]):
    with ui.card(full_screen=True):
        ui.card_header("Population density by state")

        @render_geolibre
        def map():
            m = Map(center=(-98.5, 39.8), zoom=4)
            layer_id = m.add_choropleth(
                STATES_GEOJSON, column="density", name="Population density", class_count=6
            )
            layer = m.get_layer(layer_id)
            m.set_popup(
                layer,
                [{"field": "name", "label": "State"}, {"field": "density", "label": "Density"}],
                title="name",
                show_feature_id=False,
            )
            m.set_identify(layer)
            m.show_control("measure", collapsed=True)
            return m

    with ui.card():
        ui.card_header("10 densest states (click a row to fly there)")

        @render.data_frame
        def table():
            shown = DENSEST_10[["name", "density"]].round({"density": 1})
            return render.DataGrid(shown, selection_mode="row")

    with ui.card(full_screen=True):
        ui.card_header("States currently on screen")

        @render.plot
        def visible_states():
            # "bbox" fills in once the browser's first sync lands, a moment
            # after the app boots -- req() cancels the output until then.
            bbox = map.read("project")["mapView"].get("bbox")
            west, south, east, north = req(bbox)
            shown = STATES[
                STATES["lng"].between(west, east) & STATES["lat"].between(south, north)
            ].nlargest(8, "density")
            fig = Figure(figsize=(5, 3), layout="tight")
            ax = fig.subplots()
            if not shown.empty:
                ax.barh(shown["name"][::-1], shown["density"][::-1], color="#2a6fdb")
            ax.set_xlabel("People / sq mi")
            return fig

    with ui.card():
        ui.card_header("Export")

        @render.download_button(filename="density_map.png", label="Download current view (PNG)")
        async def snapshot():
            yield await map.widget.to_image_async()


@reactive.effect
def _():
    rows = table.cell_selection()["rows"]
    if not rows:
        return
    row = DENSEST_10.iloc[rows[0]]
    map.widget.set_center(row["lng"], row["lat"], zoom=7)
