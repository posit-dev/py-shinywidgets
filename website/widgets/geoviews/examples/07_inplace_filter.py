# A magnitude slider filters 6,000 synthetic earthquakes without losing the
# user's zoom: the slider drives a holoviews.streams.Pipe, not a re-render.
# This is the same recipe as ../holoviews/guide.md's Pipe example -- see
# "Updating the widget from Python" there for the re-render-vs-in-place
# contrast in full. Synthetic data here is about *scale* (see "Performance
# with large point sets" in the guide text); the belt shape is just for
# visual plausibility.
import geoviews as gv
import holoviews as hv
import numpy as np
from shiny import reactive
from shiny.express import input, ui

from shinywidgets import render_holoviews

hv.extension("bokeh")

rng = np.random.default_rng(1)
# Two separate belts (Americas, Asia-Pacific) -- kept apart so linear
# interpolation never cuts straight across the Pacific at the antimeridian.
BELTS = [
    np.array([(-70, -55), (-71, -33), (-75, -10), (-80, 5), (-90, 15),
               (-100, 20), (-120, 35), (-125, 48), (-150, 60), (-170, 55)]),
    np.array([(170, 52), (150, 45), (140, 35), (130, 30), (125, 10),
               (120, 0), (110, -8), (130, -8), (150, -10), (170, -15), (178, -20)]),
]
lons, lats = [], []
for belt in BELTS:
    for a, b in zip(belt[:-1], belt[1:]):
        t = rng.uniform(0, 1, 320)
        seg = a * (1 - t[:, None]) + b * t[:, None] + rng.normal(0, 1.5, (320, 2))
        lons.append(seg[:, 0])
        lats.append(seg[:, 1])
lons, lats = np.concatenate(lons), np.concatenate(lats)
n = len(lons)
mag = rng.exponential(0.6, n).clip(0, 4) + 4.0  # Gutenberg-Richter-ish tail
depth = rng.gamma(2.0, 60, n).clip(0, 700)
quakes = {"lon": lons, "lat": lats, "mag": mag, "depth": depth}

ui.page_opts(title="6,000 synthetic earthquakes: filter without losing zoom", fillable=True)
ui.input_slider("min_mag", "Minimum magnitude", min=4.0, max=7.5, value=4.0, step=0.5)

pipe = hv.streams.Pipe(data=quakes)


def quake_points(data):
    return gv.Points(data, kdims=["lon", "lat"], vdims=["mag", "depth"]).opts(
        color="depth", cmap="fire_r", size=hv.dim("mag") * 1.5, alpha=0.6,
        colorbar=True, tools=["hover", "wheel_zoom"], active_tools=["wheel_zoom"],
    )


with ui.card(full_screen=True):

    @render_holoviews
    def map():
        dmap = hv.DynamicMap(quake_points, streams=[pipe])
        return (gv.tile_sources.EsriWorldDarkGrayBase * dmap).opts(responsive=True)


@reactive.effect
def _():
    mask = mag >= input.min_mag()
    pipe.send({"lon": lons[mask], "lat": lats[mask], "mag": mag[mask], "depth": depth[mask]})
