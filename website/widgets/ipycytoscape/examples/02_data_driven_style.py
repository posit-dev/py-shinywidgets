import networkx as nx
from ipycytoscape import CytoscapeWidget
from shiny.express import ui
from shinywidgets import render_ipycytoscape

G = nx.les_miserables_graph()
for n in G.nodes:
    G.nodes[n]["degree"] = G.degree(n)

STYLE = [
    {
        "selector": "node",
        "style": {
            "background-color": "#447099",
            "width": "mapData(degree, 1, 36, 10, 46)",
            "height": "mapData(degree, 1, 36, 10, 46)",
        },
    },
    {
        "selector": "node[degree >= 15]",
        "style": {"label": "data(id)", "font-size": "10px", "color": "#212529"},
    },
    {
        "selector": "edge",
        "style": {
            "width": "mapData(weight, 1, 31, 0.5, 8)",
            "line-color": "#c9d6e8",
            "curve-style": "haystack",
        },
    },
]

ui.page_opts(title="Les Misérables: degree and co-appearance weight", fillable=True)

with ui.card(full_screen=True):

    @render_ipycytoscape
    def network():
        widget = CytoscapeWidget(G)
        widget.set_style(STYLE)
        widget.set_layout(name="cose", idealEdgeLength=80, nodeRepulsion=8000)
        return widget
