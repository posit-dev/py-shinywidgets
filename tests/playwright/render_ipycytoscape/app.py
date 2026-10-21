from __future__ import annotations

import networkx as nx
from shiny import App, reactive, render, ui
from shinywidgets import output_widget, render_ipycytoscape

app_ui = ui.page_fluid(
    ui.input_action_button("rerender", "Rerender"),
    ui.output_text("render_count"),
    output_widget("graph", height="400px"),
    ui.output_text("clicked"),
)


def server(input, output, session):
    clicked_node = reactive.value("none")

    @render.text
    def render_count():
        return str(input.rerender())

    @render_ipycytoscape
    def graph():
        input.rerender()
        g = nx.Graph()
        g.add_node("solo")
        return g

    @reactive.effect
    def _():
        widget = graph.widget
        widget.set_layout(name="grid")

        def on_click(node: dict) -> None:
            clicked_node.set(node["data"]["id"])

        widget.on("node", "click", on_click)

    @render.text
    def clicked():
        return clicked_node.get()


app = App(app_ui, server)
