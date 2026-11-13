# Linked view: a Mosaic brush highlights matching points on a lonboard map.
#
# Pairs with: lonboard. The map isn't re-rendered on every brush move -- its
# layer's colors are updated in place (`reactive.isolate()` + assignment),
# which keeps the map's pan/zoom state untouched.
#
# Synthetic store locations (a small bundled dataset with this lon/lat/revenue
# shape isn't readily available) spread across the continental US.

from __future__ import annotations

import geopandas as gpd
import numpy as np
import pandas as pd
from lonboard import Map, ScatterplotLayer
from mosaic_widget import MosaicWidget
from shiny import reactive
from shiny.express import ui
from shinywidgets import render_lonboard, render_mosaic_widget

rng = np.random.default_rng(3)
n = 1500
stores = pd.DataFrame(
    {
        "id": np.arange(n),
        "lon": rng.uniform(-124, -70, n),
        "lat": rng.uniform(26, 48, n),
        "revenue": rng.gamma(2.0, 4000, n),
    }
)
GDF = gpd.GeoDataFrame(geometry=gpd.points_from_xy(stores.lon, stores.lat), crs="EPSG:4326")
DIM, BRIGHT = (120, 140, 200, 140), (255, 140, 0, 255)

spec = {
    "params": {"brush": {"select": "crossfilter"}},
    "plot": [
        {
            "mark": "rectY",
            "data": {"from": "stores"},
            "x": {"bin": "revenue"},
            "y": {"count": ""},
            "fill": "steelblue",
            "inset": 0.5,
        },
        {"select": "intervalX", "as": "$brush"},
    ],
    "xDomain": "Fixed",
    "width": 600,
    "height": 220,
}

ui.page_opts(title="Mosaic + lonboard", fillable=True)

with ui.layout_columns(col_widths=[6, 6]):
    with ui.card(full_screen=True):

        @render_mosaic_widget
        def dashboard():
            return MosaicWidget(spec, data={"stores": stores})

    with ui.card(full_screen=True):

        @render_lonboard
        def geo_map():
            colors = np.array([DIM] * n, dtype=np.uint8)
            layer = ScatterplotLayer.from_geopandas(
                GDF, get_fill_color=colors, radius_units="pixels", get_radius=4
            )
            return Map(layer)

        @reactive.effect
        def _highlight():
            params = dashboard.params()
            active = params.get("brush", {}).get("predicate", "").strip() != ""
            if active:
                selected_ids = {row[0] for row in dashboard.data().select("id").fetchall()}
                colors = np.array(
                    [BRIGHT if i in selected_ids else DIM for i in stores.id], dtype=np.uint8
                )
            else:
                colors = np.array([DIM] * n, dtype=np.uint8)
            with reactive.isolate():
                w = geo_map.widget
                if w is not None:
                    w.layers[0].get_fill_color = colors
