from __future__ import annotations

from perspective.widget import PerspectiveWidget
from shiny import App, ui
from shinywidgets import output_widget, render_perspective

app_ui = ui.page_fillable(
    ui.card(output_widget("viewer"), fill=False),
)


def server(input, output, session):
    @render_perspective
    def viewer():
        widget = PerspectiveWidget({"id": list(range(100))})
        widget.layout.height = "320px"
        return widget


app = App(app_ui, server)
