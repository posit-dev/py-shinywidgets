from __future__ import annotations

import networkx as nx
import pandas as pd
from ipysigma import Sigma
from shiny.express import render, ui
from shinywidgets import render_ipysigma

G = nx.karate_club_graph()
members = pd.DataFrame(
    {"member": list(G.nodes), "club": [G.nodes[n]["club"] for n in G.nodes]}
)

ui.page_opts(title="ipysigma legend filter", fillable=True)

with ui.layout_columns(col_widths=[7, 5]):
    with ui.card(full_screen=True):
        ui.card_header("Click a swatch in the legend to filter by club")

        @render_ipysigma
        def graph():
            return Sigma(G, node_color="club")

    with ui.card(full_screen=True):
        ui.card_header("Visible members")

        @render.data_frame
        def visible():
            # [] (nothing filtered) means "show everything", not "show nothing"
            categories = graph.read("selected_node_category_values")
            shown = members if not categories else members[members["club"].isin(categories)]
            return shown.reset_index(drop=True)
