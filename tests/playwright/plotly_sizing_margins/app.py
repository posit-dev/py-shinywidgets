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
        # Drive the template from the click count: layout.template is a
        # Template object, so comparing it to a string doesn't work
        template = "plotly_dark" if input.dark() % 2 == 1 else "plotly"
        fixed.widget.update_layout(template=template)


app = App(app_ui, server)
