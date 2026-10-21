from __future__ import annotations

import plotly.express as px
from shiny import App, ui
from shinywidgets import output_widget, render_plotly

app_ui = ui.page_fluid(
    output_widget("no_modebar"),
    output_widget("with_modebar"),
)


def server(input, output, session):
    @render_plotly
    def no_modebar():
        fig = px.histogram(px.data.tips(), x="total_bill")
        # Dash-style (figure, config) tuple
        return fig, {"displayModeBar": False}

    @render_plotly
    def with_modebar():
        # a plain figure keeps plotly's defaults (modebar visible on hover)
        return px.histogram(px.data.tips(), x="total_bill")


app = App(app_ui, server)
