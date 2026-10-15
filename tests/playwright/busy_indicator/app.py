from __future__ import annotations

import asyncio

import plotly.graph_objects as go
from shiny import App, reactive, ui
from shinywidgets import output_widget, render_widget

app_ui = ui.page_fillable(
    ui.input_action_button("submit", "Submit"),
    ui.card(
        ui.card_header("Card 1"),
        output_widget("plot"),
    ),
)


def server(input, output, session):
    @reactive.calc
    @reactive.event(input.submit)
    async def analysis_result():
        await asyncio.sleep(4)
        return [1, 2, 3]

    @render_widget
    async def plot():
        y = await analysis_result()
        return go.FigureWidget(data=[go.Scatter(x=[1, 2, 3], y=y)])


app = App(app_ui, server)
