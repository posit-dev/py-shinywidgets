from __future__ import annotations

import networkx as nx
from ipysigma import Sigma
from shiny.express import render, ui
from shinywidgets import render_ipysigma

G = nx.karate_club_graph()

ui.page_opts(title="ipysigma click to detail", fillable=True)

with ui.layout_columns(col_widths=[8, 4]):
    with ui.card(full_screen=True):
        ui.card_header("Click a member")

        @render_ipysigma
        def graph():
            return Sigma(G, node_color="club", node_size=G.degree)

    with ui.card():
        ui.card_header("Detail")

        @render.ui
        def detail():
            raw = graph.read("selected_node")
            if raw is None:
                return ui.p("Click a node to see who they're friends with.")
            node = int(raw)  # selected_node is always a string
            friends = sorted(G.neighbors(node))
            return ui.TagList(
                ui.h5(f"Member {node}"),
                ui.p(f"Club: {G.nodes[node]['club']}"),
                ui.p(f"Friends ({len(friends)}): {', '.join(map(str, friends))}"),
            )
