from bokeh.plotting import figure
from jupyter_bokeh import BokehModel
from shiny import App, Inputs, Outputs, Session, ui
from shinywidgets import bokeh_dependency, output_widget, render_bokeh, render_widget
from starlette.applications import Starlette
from starlette.routing import Mount


class CustomBokehModel(BokehModel):
    pass


def server(input: Inputs, output: Outputs, session: Session) -> None:
    @render_bokeh
    def plot() -> figure:
        chart = figure(width=300, height=200)
        chart.line([1, 2, 3], [1, 4, 9])
        return chart

    @render_widget
    def widget() -> BokehModel:
        chart = figure(width=300, height=200)
        chart.scatter([1, 2, 3], [1, 4, 9])
        return CustomBokehModel(chart)


automatic = App(ui.page_fluid(output_widget("plot"), output_widget("widget")), server)
explicit = App(
    ui.page_fluid(bokeh_dependency(), output_widget("plot"), output_widget("widget")),
    server,
)
app = Starlette(
    routes=[
        Mount("/anonymous", app=automatic),
        Mount("/explicit", app=explicit),
        Mount("/", app=automatic),
    ]
)
