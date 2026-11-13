import numpy as np
from matplotlib.figure import Figure
from shiny import reactive
from shiny.express import input, ui
from shinywidgets import render_matplotlib

ui.page_opts(fillable=True)
ui.input_slider("freq", "Frequency", 1, 10, 3)

x = np.linspace(0, 1, 400)


def base_plot():
    fig = Figure(layout="constrained", figsize=(4, 3))
    ax = fig.subplots()
    ax.plot(x, np.sin(2 * np.pi * 3 * x))
    ax.set_ylim(-1.1, 1.1)
    return fig


with ui.layout_columns():
    with ui.card(full_screen=True):
        ui.card_header("Re-render: rebuilds the figure, zoom resets")

        @render_matplotlib
        def rerendered():
            fig = Figure(layout="constrained", figsize=(4, 3))
            ax = fig.subplots()
            ax.plot(x, np.sin(2 * np.pi * input.freq() * x))
            ax.set_ylim(-1.1, 1.1)
            return fig

    with ui.card(full_screen=True):
        ui.card_header("In-place: edits the line, zoom survives")

        @render_matplotlib
        def inplace():
            # Doesn't depend on input.freq(): built once, edited afterward
            return base_plot()


@reactive.effect
def _():
    with reactive.isolate():
        canvas = inplace.widget
    if canvas is None:
        return
    line = canvas.figure.axes[0].lines[0]
    line.set_ydata(np.sin(2 * np.pi * input.freq() * x))
    canvas.draw_idle()
