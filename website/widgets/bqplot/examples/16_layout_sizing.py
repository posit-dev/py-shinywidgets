# By default a figure fills its card. render_bqplot(height=...) sets an
# exact pixel height instead; Figure(layout={"height": ...}) does the same
# thing one level down, and also opts the output out of filling.
import bqplot
from shiny.express import ui
from shinywidgets import render_bqplot

ui.page_opts(title="Layout and sizing", fillable=True)


def line_fig(title: str, **kwargs: object) -> bqplot.Figure:
    x_sc, y_sc = bqplot.LinearScale(), bqplot.LinearScale()
    line = bqplot.Lines(x=[1, 2, 3], y=[1, 3, 2], scales={"x": x_sc, "y": y_sc})
    return bqplot.Figure(
        marks=[line],
        axes=[bqplot.Axis(scale=x_sc), bqplot.Axis(scale=y_sc, orientation="vertical")],
        title=title,
        **kwargs,
    )


with ui.layout_columns():
    with ui.card(full_screen=True):
        ui.card_header("Fills the card")

        @render_bqplot
        def fills():
            return line_fig("fill")

    with ui.card():
        ui.card_header("render_bqplot(height=...)")

        @render_bqplot(height="220px")
        def fixed():
            return line_fig("220px")

    with ui.card():
        ui.card_header("Figure(layout={'height': ...})")

        @render_bqplot
        def own_height():
            return line_fig("300px, own layout", layout={"height": "300px"})
