import networkx as nx
from ipycytoscape import CytoscapeWidget
from shiny.express import render, ui
from shinywidgets import render_ipycytoscape

# A small corner of the Les Miserables co-appearance graph, with fixed
# positions so every edge lands in a predictable spot
G = (
    nx.les_miserables_graph()
    .subgraph(["Valjean", "Cosette", "Javert", "Marius"])
    .copy()
)
POSITIONS = {
    "Valjean": (200, 150),
    "Cosette": (400, 150),
    "Javert": (200, 300),
    "Marius": (400, 300),
}

STYLE = [
    {"selector": "node", "style": {"label": "data(id)"}},
    {"selector": "edge", "style": {"width": "mapData(weight, 1, 31, 1, 10)"}},
]

ui.page_opts(title="clicked_edge()", fillable=True)

with ui.layout_columns(col_widths=[8, 4]):
    with ui.card(full_screen=True):

        @render_ipycytoscape
        def network():
            widget = CytoscapeWidget(G)
            widget.set_style(STYLE)
            for node in widget.graph.nodes:
                node.position = {
                    "x": POSITIONS[node.data["id"]][0],
                    "y": POSITIONS[node.data["id"]][1],
                }
            widget.set_layout(name="preset", fit=True, padding=40)
            return widget

    with ui.card():
        ui.card_header("Clicked tie")

        @render.ui
        def detail():
            clicked = network.clicked_edge()
            if clicked is None:
                return ui.p("Click an edge to see the shared scene count.")
            d = clicked["data"]
            return ui.p(f"{d['source']} and {d['target']} share {d['weight']} scenes.")
