import os

import geopandas as gpd
import numpy as np
from lonboard import Map, ScatterplotLayer
from shiny.express import ui
from shinywidgets import render_lonboard

N = int(os.environ.get("PERF_N", "10000"))
rng = np.random.default_rng(42)
lon = rng.uniform(-122.6, -122.3, N)
lat = rng.uniform(37.6, 37.85, N)
POINTS = gpd.GeoDataFrame(geometry=gpd.points_from_xy(lon, lat), crs="EPSG:4326")

ui.page_opts(title=f"lonboard: {N:,} points", fillable=True)


@render_lonboard
def map():
    layer = ScatterplotLayer.from_geopandas(POINTS, get_radius=20)
    return Map(layer)
