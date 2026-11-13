# Shiny inputs (a landmark filter, an aggregator choice) drive the SAME
# rasterized plot in place instead of returning a new object from the render
# function: a per-session param.Parameterized holds the current choices,
# hv.streams.Params rebuilds the input points when the filter changes, and
# rasterize's aggregator accepts a param reference directly. Both update
# without resetting the user's zoom/pan (try zooming in first).
import datashader as ds
import holoviews as hv
import numpy as np
import pandas as pd
import param
from holoviews.operation.datashader import rasterize
from holoviews.streams import Params
from shiny import reactive
from shiny.express import input, ui

from shinywidgets import render_holoviews

hv.extension("bokeh")

N = 500_000
LANDMARKS = {
    "Times Square": (40.758, -73.985, 0.010),
    "Wall Street": (40.706, -74.009, 0.006),
    "JFK Airport": (40.641, -73.778, 0.020),
}
rng = np.random.default_rng(0)
names = list(LANDMARKS)
weights = rng.dirichlet(np.ones(len(names)) * 3)
counts = rng.multinomial(N, weights)
lat, lon, place = [], [], []
for name, c in zip(names, counts):
    lat0, lon0, spread = LANDMARKS[name]
    lat.append(rng.normal(lat0, spread, c))
    lon.append(rng.normal(lon0, spread, c))
    place.extend([name] * c)
pickups = pd.DataFrame({"lat": np.concatenate(lat), "lon": np.concatenate(lon), "place": pd.Categorical(place)})
pickups["fare"] = rng.gamma(2.0, 6.0, len(pickups))

ui.page_opts(title="Inputs update the plot in place", fillable=True)
ui.input_selectize("places", "Landmarks", choices=names, selected=names, multiple=True)
ui.input_radio_buttons("agg", "Aggregator", choices=["count", "mean fare"], selected="count")


class Style(param.Parameterized):
    categories = param.List(default=names)
    agg = param.Parameter(default=ds.count())


style = Style()  # one per session (Express re-runs this module per session)


def make_points(categories):
    sub = pickups[pickups.place.isin(categories)]
    return hv.Points(sub, ["lon", "lat"], ["fare"])


@reactive.effect
def _update_style():
    style.categories = list(input.places())
    style.agg = ds.count() if input.agg() == "count" else ds.mean("fare")


@render_holoviews
def plot():
    points_dmap = hv.DynamicMap(make_points, streams=[Params(style, ["categories"])])
    return rasterize(points_dmap, aggregator=style.param.agg).opts(
        responsive=True, cmap="fire", cnorm="eq_hist", colorbar=True,
    )
