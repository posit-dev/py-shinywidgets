from __future__ import annotations

import networkx as nx
from ipysigma import Sigma
from shiny.express import ui
from shinywidgets import render_ipysigma

G = nx.karate_club_graph()

ui.page_opts(title="ipysigma linked views", fillable=True)

with ui.layout_columns(col_widths=[6, 6]):
    with ui.card(full_screen=True):
        ui.card_header("By club")

        @render_ipysigma
        def by_club():
            # sync_key links pan/zoom/selection/hover between every Sigma that
            # shares it, even across separate outputs
            return Sigma(G, node_color="club", sync_key="karate")

    with ui.card(full_screen=True):
        ui.card_header("By friend count")

        @render_ipysigma
        def by_degree():
            return Sigma(
                G,
                node_color=dict(G.degree()),
                node_color_gradient=("#dbe9f6", "#08306b"),
                sync_key="karate",
            )
