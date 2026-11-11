from __future__ import annotations

from ipycytoscape import CytoscapeWidget
from shiny import App, render, ui
from shinywidgets import output_widget, render_ipycytoscape

app_ui = ui.page_fluid(
    ui.input_action_button("rerender", "Rerender"),
    output_widget("graph", height="350px"),
    ui.output_text("node"),
    ui.output_text("edge"),
    ui.output_text("selected_nodes"),
    ui.output_text("selected_edges"),
)

# Deterministic geometry: the tests click these canvas coordinates
NODE_POSITIONS = {"a": (100, 175), "b": (300, 175), "c": (200, 75)}


def server(input, output, session):
    @render_ipycytoscape
    def graph():
        input.rerender()
        import networkx as nx

        widget = CytoscapeWidget(auto_unselectify=False)
        g = nx.Graph()
        g.add_edges_from([("a", "b"), ("b", "c")])
        widget.graph.add_graph_from_networkx(g)
        for node in widget.graph.nodes:
            x, y = NODE_POSITIONS[node.data["id"]]
            node.position = {"x": x, "y": y}
            node.selectable = True
        for edge in widget.graph.edges:
            edge.selectable = True
        widget.set_layout(name="preset", padding=0, fit=False)
        return widget

    @render.text
    def node():
        d = graph.clicked_node()
        return "None" if d is None else d["data"]["id"]

    @render.text
    def edge():
        d = graph.clicked_edge()
        return "None" if d is None else f"{d['data']['source']}->{d['data']['target']}"

    @render.text
    def selected_nodes():
        return ",".join(d["id"] for d in graph.selected_nodes()) or "None"

    @render.text
    def selected_edges():
        return (
            ",".join(f"{d['source']}->{d['target']}" for d in graph.selected_edges())
            or "None"
        )


app = App(app_ui, server)
