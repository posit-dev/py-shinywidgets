from __future__ import annotations

import ipycytoscape
import networkx as nx
from shiny import App, reactive, render, ui
from shinywidgets import output_widget, render_ipycytoscape

app_ui = ui.page_fluid(
    ui.input_action_button("rerender", "Rerender"),
    ui.output_text("render_count"),
    output_widget("graph", height="400px"),
    ui.output_text("clicked"),
    ui.output_text("hovered"),
)


def server(input, output, session):
    clicked_node = reactive.value("none")
    hovered_node = reactive.value("none")

    @render.text
    def render_count():
        return str(input.rerender())

    @render_ipycytoscape
    def graph():
        input.rerender()
        g = nx.Graph()
        g.add_node("solo")
        widget = ipycytoscape.CytoscapeWidget(g)

        def on_click(node: dict) -> None:
            clicked_node.set(node["data"]["id"])

        def on_hover(node: dict) -> None:
            hovered_node.set(node["data"]["id"])

        # Register callbacks before the widget is displayed: ipycytoscape only
        # wires up the first event type per element type for later registrations
        widget.on("node", "click", on_click)
        widget.on("node", "mouseover", on_hover)
        return widget

    @reactive.effect
    def _():
        graph.widget.set_layout(name="grid")

    @render.text
    def clicked():
        return clicked_node.get()

    @render.text
    def hovered():
        return hovered_node.get()


app = App(app_ui, server)
