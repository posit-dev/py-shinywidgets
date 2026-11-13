# Re-rendering rebuilds the figure (and its scales), so any PanZoom state is
# lost. Mutating the existing mark's data preserves zoom/pan and animates.
# reactive.isolate() reads .widget without tying this effect to the render.
import bqplot
import numpy as np
from shiny import reactive
from shiny.express import input, ui
from shinywidgets import render_bqplot

ui.page_opts(title="In-place vs re-render", fillable=True)
ui.input_slider("phase", "Phase shift", 0, 10, 0, step=0.5)

x = np.linspace(0, 10, 200)


def panzoom_fig(y: np.ndarray) -> bqplot.Figure:
    x_sc, y_sc = bqplot.LinearScale(), bqplot.LinearScale()
    line = bqplot.Lines(x=x, y=y, scales={"x": x_sc, "y": y_sc})
    return bqplot.Figure(
        marks=[line], interaction=bqplot.interacts.PanZoom(scales={"x": [x_sc], "y": [y_sc]})
    )


with ui.layout_columns():
    with ui.card(full_screen=True):
        ui.card_header("Re-render: zoom resets on every change")

        @render_bqplot
        def rerendered():
            return panzoom_fig(np.sin(x + input.phase()))

    with ui.card(full_screen=True):
        ui.card_header("In-place: zoom survives, the line animates")

        @render_bqplot
        def inplace():
            # Doesn't depend on input.phase(): built once, edited afterward
            fig = panzoom_fig(np.sin(x))
            fig.animation_duration = 400
            return fig


@reactive.effect
def _update_inplace():
    phase = input.phase()
    with reactive.isolate():
        fig = inplace.widget
    fig.marks[0].y = np.sin(x + phase)
