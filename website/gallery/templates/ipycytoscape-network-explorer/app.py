# Title: Network explorer
# Summary: A small, adaptable starting point for exploring any networkx
#     graph: pick a layout, click a node to see its neighbors. Swap in your
#     own graph by replacing GRAPHS below.
# Bucket: template
# Widgets: ipycytoscape
# Pattern: click -> neighbor detail, in-place re-layout
# Run: uv run shiny run app.py
# Data: networkx's bundled karate_club_graph() and les_miserables_graph()
#
# Source: docs/widget-guides/ipycytoscape/gallery/template_network_explorer.py

import networkx as nx
from ipycytoscape import CytoscapeWidget
from shiny import reactive
from shiny.express import input, render, ui
from shinywidgets import render_ipycytoscape

GRAPHS = {
    "Karate club": nx.karate_club_graph(),
    "Les Misérables": nx.les_miserables_graph(),
}
LAYOUTS = ["concentric", "cose", "breadthfirst", "circle"]
STYLE = [
    {"selector": "node", "style": {"background-color": "#447099"}},
    {"selector": "node.focus", "style": {"background-color": "#e15759"}},
]

ui.page_opts(title="Network explorer", fillable=True)
with ui.sidebar():
    ui.input_select("graph", "Graph", list(GRAPHS))
    ui.input_select("layout", "Layout", LAYOUTS)

    @render.ui
    def detail():
        clicked = network.clicked_node()
        g = GRAPHS[input.graph()]
        # Cytoscape node ids are always strings; look up the original networkx
        # id. Clicks are kept across re-renders (switching graphs re-renders
        # `network`), so a click from the *previous* graph can still be set
        # here -- `next(..., None)` treats an id that doesn't exist in the
        # current graph the same as no click yet, instead of crashing.
        node_id = (
            next((n for n in g.nodes if str(n) == clicked["data"]["id"]), None)
            if clicked is not None
            else None
        )
        if node_id is None:
            return ui.p("Click a node to see its neighbors.", class_="text-muted")
        neighbors = sorted(map(str, g.neighbors(node_id)))
        return ui.TagList(
            ui.h5(str(node_id)),
            ui.p(
                f"{len(neighbors)} connections: {', '.join(neighbors)}", class_="small"
            ),
        )


with ui.card(full_screen=True):

    @render_ipycytoscape
    def network():
        g = GRAPHS[input.graph()]
        widget = CytoscapeWidget(g)
        widget.set_style(STYLE)
        with reactive.isolate():
            widget.set_layout(name=input.layout())
        return widget

    @reactive.effect
    def _():
        network.widget.set_layout(name=input.layout())

    @reactive.effect
    def _():
        clicked = network.clicked_node()
        focus_id = clicked["data"]["id"] if clicked else None
        for node in network.widget.graph.nodes:
            node.classes = "focus" if node.data["id"] == focus_id else ""
