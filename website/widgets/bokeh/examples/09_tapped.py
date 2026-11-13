from bokeh.plotting import figure
from shiny import req
from shiny.express import render, ui
from shinywidgets import render_bokeh

ui.page_opts(title="tapped()", fillable=True)

with ui.layout_columns(col_widths=[8, 4]):
    with ui.card(full_screen=True):

        @render_bokeh
        def plot():
            p = figure(x_range=(0, 10), y_range=(0, 10), tools="tap", title="Click anywhere")
            p.scatter([2, 5, 8], [2, 5, 8], size=20)
            return p

    with ui.card():
        ui.card_header("plot.tapped()")

        @render.text
        def coords():
            t = req(plot.tapped())
            return f"({t.x:.2f}, {t.y:.2f})"
