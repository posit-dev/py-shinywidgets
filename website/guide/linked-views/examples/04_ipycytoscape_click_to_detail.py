import networkx as nx
from ipycytoscape import CytoscapeWidget
from shiny import reactive
from shiny.express import render, ui
from shinywidgets import render_ipycytoscape

G = nx.les_miserables_graph()
STYLE = [
    {"selector": "node", "style": {"background-color": "#447099"}},
    {"selector": "node[degree >= 15]", "style": {"label": "data(id)"}},
    {"selector": ".faded", "style": {"opacity": 0.1, "text-opacity": 0}},
    {"selector": "node.focus", "style": {"border-width": 3, "border-color": "#212529"}},
]
for n in G.nodes:
    G.nodes[n]["degree"] = G.degree(n)

ui.page_opts(title="Click to highlight a neighborhood", fillable=True)

with ui.layout_columns(col_widths=[8, 4]):
    with ui.card(full_screen=True):

        @render_ipycytoscape
        def network():
            widget = CytoscapeWidget(G)
            widget.set_style(STYLE)
            widget.set_layout(name="concentric")
            return widget

    with ui.card():
        ui.card_header("Selected character")

        @render.ui
        def detail():
            clicked = network.clicked_node()
            if clicked is None:
                return ui.p("Click a character to see their circle.")
            name = clicked["data"]["id"]
            return ui.p(f"{name} and {G.degree(name)} co-characters are highlighted.")

    @reactive.effect
    def _():
        # Restyle in place by toggling classes: the layout never reruns and
        # the user's pan/zoom is kept
        clicked = network.clicked_node()
        center = clicked["data"]["id"] if clicked else None
        focus = {center, *G[center]} if center else set()
        for node in network.widget.graph.nodes:
            name = node.data["id"]
            if not focus:
                node.classes = ""
            else:
                node.classes = (
                    "focus" if name == center else "" if name in focus else "faded"
                )
        for edge in network.widget.graph.edges:
            s, t = edge.data["source"], edge.data["target"]
            edge.classes = "" if not focus or center in (s, t) else "faded"
