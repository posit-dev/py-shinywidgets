# The common "show/hide a widget panel" pattern: render.ui toggles an
# output_widget, and the widget's render depends on an input that changes
# while the panel is hidden.
import ipywidgets as W
from shiny import App, render, ui
from shinywidgets import output_widget, render_widget

app_ui = ui.page_fluid(
    ui.input_checkbox("show", "Show widget", True),
    ui.input_slider("n", "n", 0, 10, 0),
    ui.output_ui("panel"),
)


def server(input, output, session):
    @render.ui
    def panel():
        return output_widget("w") if input.show() else ui.p("hidden")

    @render_widget
    def w():
        return W.Button(description=f"n = {input.n()}")


app = App(app_ui, server)
