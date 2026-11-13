from __future__ import annotations

import networkx as nx
from shiny.express import ui
from shinywidgets import render_ipysigma

ui.page_opts(title="ipysigma quickstart", fillable=True)

with ui.card(full_screen=True):
    ui.card_header("Zachary's karate club (34 members, 78 friendships)")

    @render_ipysigma
    def graph():
        return nx.karate_club_graph()
