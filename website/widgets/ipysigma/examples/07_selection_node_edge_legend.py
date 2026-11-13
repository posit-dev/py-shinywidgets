from __future__ import annotations

import networkx as nx
from ipysigma import Sigma
from shiny.express import render, ui
from shinywidgets import render_ipysigma

G = nx.les_miserables_graph()

ui.page_opts(title="ipysigma selection", fillable=True)

with ui.layout_columns(col_widths=[8, 4]):
    with ui.card(full_screen=True):
        ui.card_header("Click a node, click an edge, or click a legend swatch")

        @render_ipysigma
        def graph():
            return Sigma(
                G,
                node_metrics={"community": "louvain"},
                node_color="community",
                clickable_edges=True,
            )

    with ui.card():
        ui.card_header("What Python sees")

        @render.code
        def state():
            node = graph.read("selected_node")
            edge = graph.read("selected_edge")
            categories = graph.read("selected_node_category_values")
            return (
                f"selected_node:  {node!r}\n"
                f"selected_edge:  {edge!r}\n"
                f"selected_node_category_values: {categories!r}"
            )
