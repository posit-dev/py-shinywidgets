import geopandas as gpd
import numpy as np
from lonboard import Map, ScatterplotLayer
from shiny import reactive
from shiny.express import render, ui
from shinywidgets import render_lonboard

ui.page_opts(title="lonboard view_state(): debounced vs. rate_delay=0", fillable=True)

rng = np.random.default_rng(42)
lon = rng.uniform(-122.6, -122.3, 2000)
lat = rng.uniform(37.6, 37.85, 2000)
POINTS = gpd.GeoDataFrame(geometry=gpd.points_from_xy(lon, lat), crs="EPSG:4326")


def counter():
    n = reactive.value(0)

    def bump():
        with reactive.isolate():
            n.set(n() + 1)

    return n, bump


with ui.layout_columns():
    with ui.card(full_screen=True):
        ui.card_header("default rate_policy/rate_delay")

        @render_lonboard
        def map_default():
            return Map(ScatterplotLayer.from_geopandas(POINTS, get_radius=30))

        n_default, bump_default = counter()

        @reactive.effect
        def _():
            map_default.view_state()
            bump_default()

        @render.code
        def out_default():
            return f"view_state() fired {n_default()} times"

    with ui.card(full_screen=True):
        ui.card_header("rate_delay=0 (same renderer kwarg)")

        @render_lonboard(rate_delay=0)
        def map_fast():
            return Map(ScatterplotLayer.from_geopandas(POINTS, get_radius=30))

        n_fast, bump_fast = counter()

        @reactive.effect
        def _():
            map_fast.view_state()
            bump_fast()

        @render.code
        def out_fast():
            return f"view_state() fired {n_fast()} times"
