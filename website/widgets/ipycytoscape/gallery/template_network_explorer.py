# Assigning to __doc__ (rather than a bare string literal) keeps this header
# out of the rendered page: shiny.express displays every top-level expression
# statement's value, docstrings included.
__doc__ = """
Network explorer (template)

A small, adaptable starting point for exploring any networkx graph: pick a
layout, click a node to see its neighbors. Swap in your own graph by
replacing GRAPHS below.

Run: shiny run template_network_explorer.py
Data: networkx's bundled karate_club_graph() and les_miserables_graph().
"""

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
        if clicked is None:
            return ui.p("Click a node to see its neighbors.", class_="text-muted")
        g = GRAPHS[input.graph()]
        # clicked_node() is kept across a re-render, so after switching graphs
        # it can still hold the *previous* graph's click -- an id that may not
        # exist in this one. Cytoscape node ids are always strings; look up the
        # original networkx id, falling back to "nothing clicked" if it's gone.
        node_id = next((n for n in g.nodes if str(n) == clicked["data"]["id"]), None)
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
