import numpy as np
from matplotlib.figure import Figure
from shiny.express import ui
from shinywidgets import as_widget, render_matplotlib

ui.page_opts(fillable=True)

t = np.linspace(0, 10, 300)


def line_plot():
    fig = Figure(layout="constrained")
    ax = fig.subplots()
    ax.plot(t, np.sin(t))
    return fig


with ui.layout_columns():
    with ui.card(full_screen=True):
        ui.card_header("Fills its card (default)")

        @render_matplotlib
        def fills():
            return line_plot()

    with ui.card():
        ui.card_header("Explicit height, no footer")

        @render_matplotlib(height="220px", fillable=True)
        def fixed_height():
            canvas = as_widget(line_plot())
            canvas.footer_visible = False  # header is already hidden by default
            return canvas
