from __future__ import annotations

from typing import Iterable, Optional

import plotly.graph_objects as go
from shiny import App, reactive, render, ui
from shinywidgets import output_widget, render_plotly

# plotly.py's own ("native") per-point event reports are muted by default
# (#479). Registering a trace callback inside the render function (as
# `native` does) keeps them on for that widget; `default` shows what an
# output without one gets.


def figure() -> go.Figure:
    fig = go.Figure(go.Scatter(x=[1, 2, 3, 4, 5], y=[1, 4, 9, 16, 25], mode="markers"))
    fig.update_traces(marker_size=14)
    return fig.update_layout(dragmode="select")


def indices(points: Optional[Iterable[int]]) -> str:
    return "None" if points is None else ",".join(str(i) for i in points)


app_ui = ui.page_fluid(
    ui.input_action_button("read", "Read selectedpoints"),
    ui.output_text("from_callback"),
    ui.output_text("selectedpoints"),
    ui.layout_columns(
        ui.card(output_widget("native"), height="400px"),
        ui.card(output_widget("default"), height="400px"),
    ),
)


def server(input, output, session):
    callback_points = reactive.value("None")

    @render_plotly
    def native() -> go.FigureWidget:
        fig = go.FigureWidget(figure())
        # A trace callback registered inside the render function keeps
        # plotly.py's per-point events on for this widget (muted otherwise)
        fig.data[0].on_selection(
            lambda trace, points, selector: callback_points.set(
                indices(points.point_inds)
            )
        )
        return fig

    @render_plotly
    def default():
        return figure()

    @render.text
    def from_callback():
        return callback_points()

    @render.text
    @reactive.event(input.read)
    def selectedpoints():
        return (
            f"native={indices(native.widget.data[0].selectedpoints)} "
            f"default={indices(default.widget.data[0].selectedpoints)}"
        )


app = App(app_ui, server)
