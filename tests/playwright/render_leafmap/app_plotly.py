from __future__ import annotations

from plotly.graph_objects import FigureWidget, Scatter
from shiny import App, Inputs, Outputs, Session, reactive, ui
from shinywidgets import output_widget, render_leafmap

app_ui = ui.page_fluid(
    ui.input_action_button("update", "Update markers"),
    ui.card(output_widget("plot"), id="plotly_card", height="450px"),
)


def server(input: Inputs, output: Outputs, session: Session) -> None:
    @render_leafmap
    def plot() -> FigureWidget:
        return LeafmapPlotlyMap(
            Scatter(x=[1, 2], y=[2, 1], mode="markers", marker={"color": "red"}),
            layout={"height": 600},
        )

    @reactive.effect
    @reactive.event(input.update)
    def update_plot() -> None:
        figure = plot.value
        if figure is not None:
            figure.update_traces(marker_color="blue")


class LeafmapPlotlyMap(FigureWidget):
    __module__ = "leafmap.plotlymap"


app = App(app_ui, server)
