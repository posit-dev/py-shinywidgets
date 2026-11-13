import numpy as np
from bokeh.models import ColumnDataSource
from bokeh.plotting import figure
from shiny import req
from shiny.express import render, ui
from shinywidgets import render_bokeh

ui.page_opts(title="Tap for details", fillable=True)

rng = np.random.default_rng(7)
n = 40
src = ColumnDataSource(
    {
        "x": rng.uniform(0, 10, n),
        "y": rng.uniform(0, 10, n),
        "city": [f"Station {i}" for i in range(n)],
        "temp": rng.normal(18, 5, n),
    }
)

with ui.layout_columns(col_widths=[8, 4]):
    with ui.card(full_screen=True):

        @render_bokeh
        def plot():
            p = figure(tools="tap", title="Tap a station")
            p.scatter("x", "y", source=src, size=12)
            return p

    with ui.card():
        ui.card_header("Nearest station")

        @render.ui
        def detail():
            t = req(plot.tapped())
            x, y = np.asarray(src.data["x"]), np.asarray(src.data["y"])
            i = int(np.argmin((x - t.x) ** 2 + (y - t.y) ** 2))
            return ui.TagList(
                ui.h5(src.data["city"][i]),
                ui.p(f"temperature: {src.data['temp'][i]:.1f}C"),
                ui.p(f"location: ({x[i]:.1f}, {y[i]:.1f})"),
            )
