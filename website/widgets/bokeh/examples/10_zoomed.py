import numpy as np
from bokeh.plotting import figure
from shiny import req
from shiny.express import render, ui
from shinywidgets import render_bokeh

ui.page_opts(title="zoomed()", fillable=True)

rng = np.random.default_rng(3)
x = rng.normal(size=300)
y = rng.normal(size=300)

with ui.layout_columns(col_widths=[8, 4]):
    with ui.card(full_screen=True):

        @render_bokeh
        def plot():
            p = figure(tools="pan,wheel_zoom,reset", active_scroll="wheel_zoom")
            p.scatter(x, y, size=6, alpha=0.6)
            return p

    with ui.card():
        ui.card_header("plot.zoomed()")

        @render.text
        def ranges():
            z = req(plot.zoomed())
            return (
                f"x: [{z.x0:.2f}, {z.x1:.2f}]\n"
                f"y: [{z.y0:.2f}, {z.y1:.2f}]"
            )
