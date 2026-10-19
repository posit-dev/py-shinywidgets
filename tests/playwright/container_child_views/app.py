# Two re-rendering outputs: a VBox wrapping a session-owned (shared) child
# widget, and a plain ipyleaflet map with no session children.
import ipyleaflet as L
import ipywidgets as W
from shiny import App, reactive, render, ui
from shinywidgets import output_widget, render_widget

app_ui = ui.page_fluid(
    ui.input_action_button("rerender", "Rerender"),
    ui.output_text("render_count"),
    output_widget("box"),
    output_widget("map", height="300px"),
)


def server(input, output, session):
    counter = reactive.value(0)
    shared_btn = W.Button(description="session button")

    @reactive.effect
    @reactive.event(input.rerender)
    def _():
        counter.set(counter.get() + 1)

    @render.text
    def render_count():
        return str(counter.get())

    @render_widget
    def box():
        n = counter.get()
        return W.VBox([W.Label(f"render {n}"), shared_btn])

    @render_widget
    def map():
        n = counter.get()
        m = L.Map(center=(52.2 + n * 0.001, 0.12), zoom=13)
        m.add(L.Marker(location=(52.2 + n * 0.001, 0.12)))
        return m


app = App(app_ui, server)
