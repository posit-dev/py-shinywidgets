from __future__ import annotations

import ipycytoscape
import networkx as nx
from shiny import App, ui
from shinywidgets import output_widget, render_ipycytoscape

app_ui = ui.page_fluid(
    ui.card(
        ui.card_header("fills the card"),
        output_widget("filled"),
        height="500px",
    ),
    output_widget("explicit_output_height", height="250px"),
    output_widget("explicit_widget_height"),
    output_widget("intrinsic_output_height", height="auto"),
)


def make_graph() -> nx.Graph:
    return nx.path_graph(4)


def server(input, output, session):
    @render_ipycytoscape
    def filled():
        return make_graph()

    @render_ipycytoscape
    def explicit_output_height():
        return make_graph()

    @render_ipycytoscape
    def explicit_widget_height():
        widget = ipycytoscape.CytoscapeWidget()
        widget.graph.add_graph_from_networkx(make_graph())
        widget.layout.height = "300px"
        return widget

    @render_ipycytoscape
    def intrinsic_output_height():
        return make_graph()


app = App(app_ui, server)
