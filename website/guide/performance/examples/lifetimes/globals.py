# Built once, at import time, before any session exists -- Express imports
# this sibling module before any session connects (not necessarily exactly
# once: see the "Lifetimes" article's shared_lifetime()-in-Express gotcha
# for why, and for why this can't live in the main app file directly).
import geopandas as gpd
import numpy as np
from lonboard import Map, ScatterplotLayer
from shinywidgets import shared_lifetime

N = 200_000

with shared_lifetime():
    rng = np.random.default_rng(42)
    lon = rng.uniform(-122.6, -122.3, N)
    lat = rng.uniform(37.6, 37.85, N)
    _points = gpd.GeoDataFrame(geometry=gpd.points_from_xy(lon, lat), crs="EPSG:4326")
    _layer = ScatterplotLayer.from_geopandas(_points, get_radius=20)
    SHARED_MAP = Map(_layer)
