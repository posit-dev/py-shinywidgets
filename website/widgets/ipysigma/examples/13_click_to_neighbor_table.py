from __future__ import annotations

import networkx as nx
import pandas as pd
from ipysigma import Sigma
from shiny import req
from shiny.express import render, ui
from shinywidgets import render_ipysigma

G = nx.karate_club_graph()
members = pd.DataFrame(
    {"member": list(G.nodes), "club": [G.nodes[n]["club"] for n in G.nodes]}
)

ui.page_opts(title="ipysigma click to table", fillable=True)

with ui.layout_columns(col_widths=[7, 5]):
    with ui.card(full_screen=True):
        ui.card_header("Click a member")

        @render_ipysigma
        def graph():
            return Sigma(G, node_color="club", node_size=G.degree)

    with ui.card(full_screen=True):
        ui.card_header("Their friends")

        @render.data_frame
        def neighbor_table():
            raw = graph.read("selected_node")
            req(raw)
            neighbors = sorted(G.neighbors(int(raw)))
            return members[members["member"].isin(neighbors)].reset_index(drop=True)
