from __future__ import annotations

import geopandas as gpd
import lonboard
import pandas as pd
from shiny.express import ui
from shinywidgets import render_lonboard

# Kept separate from 03_dark_mode.py: rendering a lonboard map on the same
# page as a maplibre map crashes lonboard's view (the two widgets load
# conflicting bundled copies of deck.gl), unrelated to dark
# mode. This file isolates lonboard to get a clean dark-mode screenshot.
ui.page_opts(title="lonboard: dark mode", fillable=True)
ui.input_dark_mode(id="mode")

points = pd.DataFrame({"lon": [-98.5, -100, -95, -90], "lat": [39.8, 40, 41, 38]})
cities = gpd.GeoDataFrame(
    points, geometry=gpd.points_from_xy(points.lon, points.lat), crs="EPSG:4326"
)


@render_lonboard
def map_lonboard():
    return lonboard.viz(cities)
