from __future__ import annotations

from bokeh.plotting import figure
from shiny import App, ui
from shinywidgets import bokeh_dependency, output_widget, render_bokeh
from starlette.applications import Starlette
from starlette.routing import Mount


shiny_ui = ui.page_fluid(
    output_widget("plot"),
    bokeh_dependency(),
)


def shiny_server(input, output, session):
    @render_bokeh
    def plot():
        p = figure(title="mounted")
        p.line([1, 2, 3], [1, 2, 3], line_width=2)
        return p


shiny_app = App(shiny_ui, shiny_server)
app = Starlette(routes=[Mount("/anonymous", app=shiny_app)])
