import numpy as np
from bokeh.plotting import figure
from shiny.express import ui
from shinywidgets import render_bokeh

rng = np.random.default_rng(0)
n = 200_000
x = rng.normal(size=n)
y = x * 0.5 + rng.normal(size=n)

ui.page_opts(title="WebGL vs. canvas at 200,000 points", fillable=True)

with ui.layout_columns():
    with ui.card(full_screen=True):
        ui.card_header('output_backend="webgl"')

        @render_bokeh
        def webgl_plot():
            p = figure(output_backend="webgl", title="WebGL")
            p.scatter(x, y, size=3, alpha=0.3)
            return p

    with ui.card(full_screen=True):
        ui.card_header("default (canvas)")

        @render_bokeh
        def canvas_plot():
            p = figure(title="Canvas")
            p.scatter(x, y, size=3, alpha=0.3)
            return p
