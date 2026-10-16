from bokeh.layouts import column
from bokeh.models import Column, Div
from review_ext import ExtensionDiv
from shiny import App, Inputs, Outputs, Session, ui
from shinywidgets import output_widget, render_bokeh
from starlette.applications import Starlette
from starlette.routing import Mount


def server(input: Inputs, output: Outputs, session: Session) -> None:
    @render_bokeh
    def warm() -> Div:
        return Div(text="<h2>Core Bokeh loaded</h2>")

    @render_bokeh
    def extension() -> Column | None:
        count = input.show_extension()
        if not count:
            return None
        return column(ExtensionDiv(text=f"<h3>Extension render {count}</h3>"))


shiny_app = App(
    ui.page_fluid(
        ui.input_action_button("show_extension", "Show extension"),
        output_widget("warm"),
        output_widget("extension"),
    ),
    server,
)
app = Starlette(routes=[Mount("/nested", app=shiny_app), Mount("/", app=shiny_app)])
