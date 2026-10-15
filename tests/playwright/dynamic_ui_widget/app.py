# Dynamic UI: output_widget() inserted via @render.ui (issue #108 family)
import ipywidgets as iw
from shiny import App, render, ui
from shinywidgets import output_widget, render_widget

app_ui = ui.page_fluid(
    ui.input_action_button("show", "Show widget"),
    ui.output_ui("slot"),
)


def server(input, output, session):
    @render.ui
    def slot():
        if input.show() == 0:
            return None
        return output_widget("dyn")

    @render_widget
    def dyn():
        return iw.HTML(value=f"<b>dynamic render #{input.show()}</b>")


app = App(app_ui, server)
