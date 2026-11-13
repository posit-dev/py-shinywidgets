import networkx as nx
from ipycytoscape import CytoscapeWidget
from shiny import reactive
from shiny.express import input, ui
from shinywidgets import render_ipycytoscape

G = nx.les_miserables_graph()
for n in G.nodes:
    G.nodes[n]["degree"] = G.degree(n)
STYLE = [
    {"selector": "node", "style": {"background-color": "#447099"}},
    {"selector": ".hidden", "style": {"display": "none"}},
]

ui.page_opts(title="Filter without losing the layout", fillable=True)
ui.input_slider("min_degree", "Minimum number of co-stars", 1, 20, 1)

with ui.card(full_screen=True):

    @render_ipycytoscape
    def network():
        widget = CytoscapeWidget(G)
        widget.set_style(STYLE)
        widget.set_layout(name="cose")  # computed once, from the full graph
        return widget

    @reactive.effect
    def _():
        # Hiding elements (not removing them) keeps every node's position, so
        # raising the slider back down instantly restores the full layout
        shown = {n for n in G if G.nodes[n]["degree"] >= input.min_degree()}
        for node in network.widget.graph.nodes:
            node.classes = "" if node.data["id"] in shown else "hidden"
        for edge in network.widget.graph.edges:
            s, t = edge.data["source"], edge.data["target"]
            edge.classes = "" if s in shown and t in shown else "hidden"
