import geopandas as gpd
import numpy as np
from lonboard import Map, ScatterplotLayer
from shiny import reactive
from shiny.express import input, ui
from shinywidgets import render_lonboard

ui.page_opts(title="lonboard: re-render vs in-place", fillable=True)

N = 50_000
rng = np.random.default_rng(42)
lon = rng.uniform(-122.6, -122.3, N)
lat = rng.uniform(37.6, 37.85, N)
POINTS = gpd.GeoDataFrame(geometry=gpd.points_from_xy(lon, lat), crs="EPSG:4326")

ui.input_action_button("inplace", "Update in place (set get_fill_color)")
ui.input_action_button("rerender", "Force re-render (new Map)")

color_toggle = reactive.value(False)
rerender_trigger = reactive.value(0)


# Per-point varying colors (not a constant RGB triple) so the measured
# payload reflects real per-point data, not a degenerate, highly
# compressible constant array.
_rank = np.argsort(np.argsort(lon)) / N


def colors(is_red: bool) -> np.ndarray:
    r = (_rank * 255).astype("uint8")
    out = np.zeros((N, 3), dtype="uint8")
    if is_red:
        out[:, 0] = r
        out[:, 2] = 255 - r
    else:
        out[:, 2] = r
        out[:, 0] = 255 - r
    return out


@render_lonboard
def map():
    rerender_trigger()
    with reactive.isolate():
        is_red = color_toggle()
    layer = ScatterplotLayer.from_geopandas(
        POINTS, get_fill_color=colors(is_red), get_radius=20
    )
    return Map(layer)


@reactive.effect
@reactive.event(input.inplace)
def _inplace():
    with reactive.isolate():
        is_red = not color_toggle()
    color_toggle.set(is_red)
    map.widget.layers[0].get_fill_color = colors(is_red)


@reactive.effect
@reactive.event(input.rerender)
def _rerender():
    with reactive.isolate():
        color_toggle.set(not color_toggle())
    rerender_trigger.set(rerender_trigger() + 1)
