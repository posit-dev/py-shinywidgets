from __future__ import annotations

import networkx as nx
from ipysigma import Sigma
from shiny.express import ui
from shinywidgets import render_ipysigma

G = nx.les_miserables_graph()  # co-appearance count is the "weight" edge attribute

ui.page_opts(title="ipysigma edges", fillable=True)

with ui.card(full_screen=True):
    ui.card_header("Edge thickness and color from co-appearance count")

    @render_ipysigma
    def graph():
        return Sigma(
            G,
            node_size=G.degree,
            edge_size="weight",
            edge_color="weight",
            edge_color_gradient=("#ddd", "#c0392b"),
            # Lets users click an edge (not just a node) to inspect it
            clickable_edges=True,
        )
