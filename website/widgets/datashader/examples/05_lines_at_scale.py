# Datashader rasterizes lines too, not just points: 5 synthetic sensor
# traces (200,000 samples each, 1,000,000 points total) overlaid and
# datashaded with one color per category -- a continuous line, not discrete
# markers, so individual samples never show up as clutter.
import datashader as ds
import holoviews as hv
import numpy as np
import pandas as pd
from holoviews.operation.datashader import datashade
from shiny.express import ui

from shinywidgets import render_holoviews

hv.extension("bokeh")

N_PER_SENSOR = 200_000
K = 5
rng = np.random.default_rng(0)
frames = []
for i in range(K):
    v = np.cumsum(rng.normal(0, 1, N_PER_SENSOR)) * 0.03 + i * 3
    frames.append(pd.DataFrame({"t": np.arange(N_PER_SENSOR), "v": v, "sensor": f"sensor {i}"}))
readings = pd.concat(frames, ignore_index=True)
readings["sensor"] = readings["sensor"].astype("category")

ui.page_opts(title=f"{len(readings):,} samples across {K} sensors", fillable=True)


@render_holoviews
def traces():
    overlay = hv.NdOverlay(
        {s: hv.Curve(g, "t", "v") for s, g in readings.groupby("sensor", observed=True)},
        kdims="sensor",
    )
    return datashade(
        overlay,
        aggregator=ds.count_cat("sensor"),
        color_key=hv.Cycle("Category10").values[:K],
    ).opts(responsive=True, title=f"{K} sensors, {N_PER_SENSOR:,} samples each")
