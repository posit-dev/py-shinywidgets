import holoviews as hv
import hvplot.pandas  # noqa: F401
import numpy as np
import pandas as pd
from shiny import App, ui
from shinywidgets import output_widget, render_holoviews

hv.extension("bokeh")

# A million points: far too many to send to the browser as individual glyphs.
# Datashader aggregates them on the server into an image instead.
rng = np.random.default_rng(1)
n = 1_000_000
centers = rng.uniform(-8, 8, size=(12, 2))
cluster = rng.integers(0, len(centers), n)
spread = rng.uniform(0.05, 1.5, len(centers))[cluster, None]
xy = centers[cluster] + rng.normal(size=(n, 2)) * spread
value = rng.uniform(0, 10, len(centers))[cluster] + rng.normal(size=n)
df = pd.DataFrame({"x": xy[:, 0], "y": xy[:, 1], "value": value})

app_ui = ui.page_sidebar(
    ui.sidebar(
        ui.input_select(
            "agg",
            "Aggregate",
            {"count": "Number of points", "mean": "Mean of value"},
        ),
        ui.input_select("cmap", "Colormap", ["viridis", "fire", "kbc", "blues"]),
        ui.p(
            "Zoom (scroll wheel) or pan the plot. Each time the view changes, "
            "datashader re-aggregates the data on the server for just that "
            "region, so detail that's invisible at full scale emerges as you "
            "zoom in.",
            class_="text-muted small",
        ),
    ),
    ui.card(
        ui.card_header("1,000,000 points, rasterized with datashader"),
        output_widget("points"),
        full_screen=True,
    ),
    title="datashader via @render_holoviews",
    fillable=True,
)


def server(input, output, session):
    @render_holoviews
    def points():
        # Build the plot here, per session, not once at module level (the data can
        # be shared): every display of the same holoviews object shares its zoom
        # streams, so a shared plot would apply one user's zoom to everyone's plot.
        mean = input.agg() == "mean"
        return df.hvplot.points(
            "x",
            "y",
            c="value" if mean else None,
            aggregator="mean" if mean else "count",
            clabel="Mean of value" if mean else "Number of points",
            rasterize=True,
            cmap=input.cmap(),
            cnorm="eq_hist",
            responsive=True,
        )


app = App(app_ui, server)
