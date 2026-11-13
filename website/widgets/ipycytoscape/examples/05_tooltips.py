import networkx as nx
from ipycytoscape import CytoscapeWidget
from shiny.express import ui
from shinywidgets import render_ipycytoscape

G = nx.les_miserables_graph()
for n in G.nodes:
    scenes = sorted(G[n].items(), key=lambda kv: -kv[1]["weight"])[:3]
    top = ", ".join(f"{m} ({d['weight']})" for m, d in scenes)
    G.nodes[n]["tooltip"] = f"{n}\nTop co-stars: {top}"

STYLE = [{"selector": "node", "style": {"background-color": "#447099"}}]

ui.page_opts(title="Click a node for its tooltip", fillable=True)

with ui.card(full_screen=True):

    @render_ipycytoscape
    def network():
        widget = CytoscapeWidget(G)
        widget.set_style(STYLE)
        widget.set_layout(name="concentric")
        return widget
