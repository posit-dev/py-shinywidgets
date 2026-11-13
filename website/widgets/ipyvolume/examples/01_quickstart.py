import ipyvolume as ipv
import numpy as np
import plotly.express as px
from shiny.express import ui

from shinywidgets import render_ipyvolume

iris = px.data.iris()
# Per-point color must be a numeric (N, 3) RGB array in [0, 1] -- a per-point
# array of color *strings* (e.g. "tomato") hangs ipyvolume's serializer; see
# the "Gotchas" section.
palette = np.array([[0.91, 0.30, 0.24], [0.18, 0.49, 0.20], [0.21, 0.45, 0.69]])
color = palette[iris["species_id"] - 1]

ui.page_opts(title="ipyvolume quickstart", fillable=True)


@render_ipyvolume
def plot():
    ipv.quickscatter(
        iris["sepal_length"],
        iris["petal_length"],
        iris["sepal_width"],
        size=1.2,
        marker="sphere",
        color=color,
    )
    return ipv.gcf()
