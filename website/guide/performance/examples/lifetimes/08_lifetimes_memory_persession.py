import geopandas as gpd
import numpy as np
from lonboard import Map, ScatterplotLayer
from shiny.express import ui
from shinywidgets import render_lonboard

N = 200_000

ui.page_opts(title="memory: per-session widget", fillable=True)


@render_lonboard
def map():
    # Each session builds its OWN 200k-point layer -- memory for this widget
    # scales with the number of concurrent sessions.
    rng = np.random.default_rng(42)
    lon = rng.uniform(-122.6, -122.3, N)
    lat = rng.uniform(37.6, 37.85, N)
    points = gpd.GeoDataFrame(geometry=gpd.points_from_xy(lon, lat), crs="EPSG:4326")
    layer = ScatterplotLayer.from_geopandas(points, get_radius=20)
    return Map(layer)
