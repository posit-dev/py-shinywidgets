from htmltools import Tag
from ipyleaflet import Map, Marker
from ipywidgets import HTML, DOMWidget
from shiny import App, Inputs, Outputs, Session, render, ui
from shinywidgets import output_widget, render_widget
from starlette.requests import Request


def app_ui(request: Request) -> Tag:
    return ui.page_fluid(
        ui.input_select(
            "mode",
            "Widget",
            choices=["cached", "popup", "empty", "error"],
            selected=request.query_params.get("mode", "cached"),
        ),
        ui.input_action_button("redraw", "Redraw"),
        ui.output_text("render_count"),
        output_widget("widget", height="400px"),
    )


def server(input: Inputs, output: Outputs, session: Session) -> None:
    cached = HTML("Persistent widget")

    @render.text
    def render_count() -> str:
        return str(input.redraw())

    @render_widget
    def widget() -> DOMWidget | None:
        n = input.redraw()
        mode = input.mode()
        if mode == "empty":
            return None
        if mode == "error":
            raise RuntimeError("Requested widget failure")
        if mode == "cached":
            return cached
        map = Map(center=(0, 0), zoom=4)
        marker = Marker(location=(0, 0), draggable=False)
        marker.popup = HTML(f"Popup render {n}")
        map.add(marker)
        return map


app = App(app_ui, server)
