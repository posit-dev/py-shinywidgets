from __future__ import annotations

from typing import cast

import plotly.graph_objects as go
from plotly.callbacks import InputDeviceState, Points
from shiny import App, Inputs, Outputs, Session, reactive, render, ui
from shinywidgets import output_widget, render_plotly, session_lifetime

app_ui = ui.page_fluid(
    ui.input_select("dataset", "Dataset", ["A", "B"]),
    ui.input_text("title", "Title", "updated A"),
    ui.input_action_button("update", "Update title"),
    ui.output_text("requested_title"),
    ui.output_text("update_status"),
    ui.output_text("click_count"),
    output_widget("cached_plot", height="350px"),
)


def server(input: Inputs, output: Outputs, session: Session) -> None:
    cache: dict[str, go.FigureWidget] = {}
    clicks = reactive.value(0)
    updates = reactive.value("")

    def record_click(
        trace: go.Scatter, points: Points, state: InputDeviceState
    ) -> None:
        with reactive.isolate():
            clicks.set(clicks.get() + 1)

    @render_plotly
    def cached_plot() -> go.FigureWidget:
        key = input.dataset()
        if key not in cache:
            with session_lifetime():
                figure = go.FigureWidget(
                    data=[
                        go.Scatter(x=[1, 2], y=[1, 2], mode="markers", marker_size=18)
                    ],
                    layout={"title": key},
                )
                cast(go.Scatter, figure.data[0]).on_click(record_click)
                cache[key] = figure
        return cache[key]

    @reactive.effect
    @reactive.event(input.update)
    def update_title() -> None:
        widget = cached_plot.widget
        if widget is not None:
            widget.layout.title.text = input.title()
            updates.set(f"{widget.model_id}:{widget.layout.title.text}")
        else:
            updates.set("no widget")

    @render.text
    def click_count() -> str:
        return str(clicks.get())

    @render.text
    def requested_title() -> str:
        return input.title()

    @render.text
    def update_status() -> str:
        return updates.get()


app = App(app_ui, server)
