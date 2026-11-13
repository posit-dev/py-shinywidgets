from __future__ import annotations

import networkx as nx
from ipysigma import Sigma
from shiny.express import ui
from shinywidgets import render_ipysigma

G = nx.karate_club_graph()

ui.page_opts(title="ipysigma encodings", fillable=True)

with ui.card(full_screen=True):
    ui.card_header("Colored by club, sized by friend count")

    @render_ipysigma
    def graph():
        # node_color/node_size read straight from node attributes (club) or a
        # DegreeView; ipysigma adds a clickable legend for the categorical color.
        return Sigma(G, node_color="club", node_size=G.degree)
