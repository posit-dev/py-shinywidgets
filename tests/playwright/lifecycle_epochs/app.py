import ipywidgets
from shiny import App, ui
from shinywidgets import output_widget, render_widget

app_ui = ui.page_fluid(
    output_widget("widget"),
    output_widget("button"),
)


def server(input, output, session):
    @render_widget
    def button():
        # A controls widget that uses a FontAwesome icon (drives font
        # requests against the served runtime bundle).
        return ipywidgets.Button(description="Go", icon="check")


app = App(app_ui, server)
