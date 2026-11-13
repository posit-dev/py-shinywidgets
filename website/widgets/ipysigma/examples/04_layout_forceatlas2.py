from __future__ import annotations

import networkx as nx
from ipysigma import Sigma
from shiny.express import ui
from shinywidgets import render_ipysigma

G = nx.les_miserables_graph()  # character co-occurrence in Victor Hugo's novel

ui.page_opts(title="ipysigma ForceAtlas2", fillable=True)

with ui.card(full_screen=True):
    ui.card_header("Les Misérables characters, laid out live")

    @render_ipysigma
    def graph():
        # No layout= is given, so nodes start at random positions; start_layout
        # runs ForceAtlas2 in a web worker for 4 seconds, then stops and writes
        # the converged positions back to the `layout` trait.
        return Sigma(G, start_layout=4, node_size=G.degree)
