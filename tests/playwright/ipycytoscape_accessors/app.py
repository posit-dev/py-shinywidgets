from __future__ import annotations

from ipycytoscape import CytoscapeWidget
from shiny import App, render, ui
from shinywidgets import output_widget, render_ipycytoscape

app_ui = ui.page_fluid(
    ui.input_action_button("rerender", "Rerender"),
    output_widget("graph", height="350px"),
    ui.output_text("node"),
    ui.output_text("edge"),
)

# Deterministic geometry: the tests click these canvas coordinates
NODE_POSITIONS = {"a": (100, 175), "b": (300, 175), "c": (200, 75)}


def server(input, output, session):
    @render_ipycytoscape
    def graph():
        input.rerender()
        import networkx as nx

        widget = CytoscapeWidget()
        g = nx.Graph()
        g.add_edges_from([("a", "b"), ("b", "c")])
        widget.graph.add_graph_from_networkx(g)
        for node in widget.graph.nodes:
            x, y = NODE_POSITIONS[node.data["id"]]
            node.position = {"x": x, "y": y}
        widget.set_layout(name="preset", padding=0, fit=False)
        return widget

    @render.text
    def node():
        d = graph.node_clicked()
        return "None" if d is None else d["data"]["id"]

    @render.text
    def edge():
        d = graph.edge_clicked()
        return "None" if d is None else f"{d['data']['source']}->{d['data']['target']}"


app = App(app_ui, server)
