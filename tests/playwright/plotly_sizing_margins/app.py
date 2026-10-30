from __future__ import annotations

import plotly.express as px
from shiny import App, reactive, ui
from shinywidgets import output_widget, render_plotly

app_ui = ui.page_fluid(
    ui.input_action_button("dark", "Toggle dark"),
    # An explicit output height without fillable=True: the plot should size
    # to it, not render at plotly's 360px fallback
    output_widget("fixed", height="300px", fillable=False),
    output_widget("filling", height="300px", fillable=True),
)


def server(input, output, session):
    @render_plotly
    def fixed():
        return px.histogram(px.data.tips(), x="total_bill")

    @render_plotly
    def filling():
        return px.histogram(px.data.tips(), x="total_bill")

    @reactive.effect
    @reactive.event(input.dark)
    def _():
        w = fixed.widget
        template = w.layout.template
        w.update_layout(template="plotly" if template == "plotly_dark" else "plotly_dark")


app = App(app_ui, server)
