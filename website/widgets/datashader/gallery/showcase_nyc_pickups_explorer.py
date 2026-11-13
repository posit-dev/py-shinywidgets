# NYC pickups explorer: 1,000,000 synthetic ride-hail pickups clustered
# around real NYC landmarks. Filter by landmark and switch aggregators
# without losing your zoom (param refs + hv.streams.Params update the
# rasterized plot in place), then drag a box to compute exact stats on the
# full filtered data -- not just the pixels datashader drew.
# showcase | a fuller dashboard combining in-place updates + box-select stats
# run: uv run shiny run gallery/showcase_nyc_pickups_explorer.py
# data: synthetic, clustered around real NYC landmarks (see guide.md)
import datashader as ds
import holoviews as hv
import numpy as np
import pandas as pd
import param
from holoviews.operation.datashader import rasterize
from holoviews.streams import BoundsXY, Params
from shiny import reactive
from shiny.express import input, render, ui

from shinywidgets import render_holoviews

hv.extension("bokeh")

N = 1_000_000
LANDMARKS = {
    "Times Square": (40.758, -73.985, 0.010),
    "Wall Street": (40.706, -74.009, 0.006),
    "JFK Airport": (40.641, -73.778, 0.020),
    "LaGuardia": (40.777, -73.872, 0.015),
    "Central Park": (40.782, -73.965, 0.015),
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
pickups["fare"] = rng.gamma(2.0, 6.0, len(pickups)) + (pickups.place == "JFK Airport") * 40

ui.page_opts(title="NYC pickups explorer", fillable=True)

with ui.layout_columns(col_widths=[3, 9]):
    with ui.card():
        ui.card_header("Filters")
        ui.input_selectize("places", "Landmarks", choices=names, selected=names, multiple=True)
        ui.input_radio_buttons("agg", "Aggregator", choices=["count", "mean fare"], selected="count")
        ui.hr()
        ui.h6("Box selection (drag on the plot)")

        @render.ui
        def box_stats():
            b = selected_bounds()
            if b is None:
                return ui.p("Drag a box on the plot.", class_="text-muted")
            x0, y0, x1, y1 = b
            sel = filtered()
            sel = sel[sel.lon.between(x0, x1) & sel.lat.between(y0, y1)]
            if not len(sel):
                return ui.p("No rows in that box.", class_="text-muted")
            return ui.TagList(
                ui.p(f"{len(sel):,} rows"),
                ui.p(f"mean fare: ${sel.fare.mean():.2f}"),
            )

    with ui.card(full_screen=True):

        @render_holoviews
        def plot():
            points_dmap = hv.DynamicMap(make_points, streams=[Params(style, ["categories"])])
            img = rasterize(points_dmap, aggregator=style.param.agg).opts(
                responsive=True, cmap="fire", cnorm="eq_hist", colorbar=True,
                tools=["box_select"], active_tools=["box_select"],
            )
            BoundsXY(source=img).add_subscriber(lambda bounds: selected_bounds.set(bounds))
            return img


class Style(param.Parameterized):
    categories = param.List(default=names)
    agg = param.Parameter(default=ds.count())


style = Style()  # one per session (Express re-runs this module per session)
selected_bounds = reactive.value(None)


def make_points(categories):
    sub = pickups[pickups.place.isin(categories)]
    return hv.Points(sub, ["lon", "lat"], ["fare"])


@reactive.calc
def filtered():
    return pickups[pickups.place.isin(input.places())]


@reactive.effect
def _update_style():
    style.categories = list(input.places())
    style.agg = ds.count() if input.agg() == "count" else ds.mean("fare")
    # a filter/aggregator change narrows what the current box selection means
    selected_bounds.set(None)
