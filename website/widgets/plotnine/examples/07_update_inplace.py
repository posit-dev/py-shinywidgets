import numpy as np
import pandas as pd
from plotnine import aes, geom_line, ggplot, scale_y_continuous, theme_minimal
from shiny import reactive
from shiny.express import input, ui
from shinywidgets import render_plotnine

ui.page_opts(title="Re-render vs. in-place", fillable=True)
ui.input_slider("freq", "Frequency", 1, 10, 3)

x = np.linspace(0, 1, 400)


def wave(freq: int) -> pd.DataFrame:
    return pd.DataFrame({"x": x, "y": np.sin(2 * np.pi * freq * x)})


with ui.layout_columns():
    with ui.card(full_screen=True):
        ui.card_header("Re-render: zoom resets")

        @render_plotnine
        def rerendered():
            return (
                ggplot(wave(input.freq()), aes("x", "y"))
                + geom_line()
                + scale_y_continuous(limits=(-1.1, 1.1))
                + theme_minimal()
            )

    with ui.card(full_screen=True):
        ui.card_header("In-place: zoom survives")

        @render_plotnine
        def inplace():
            # Doesn't read input.freq(): built once, edited afterward
            return (
                ggplot(wave(3), aes("x", "y"))
                + geom_line()
                + scale_y_continuous(limits=(-1.1, 1.1))
                + theme_minimal()
            )


@reactive.effect
def _update_wave():
    freq = input.freq()
    with reactive.isolate():
        canvas = inplace.widget
    if canvas is None:
        return
    line = canvas.figure.axes[0].lines[0]
    line.set_ydata(np.sin(2 * np.pi * freq * x))
    canvas.draw_idle()
