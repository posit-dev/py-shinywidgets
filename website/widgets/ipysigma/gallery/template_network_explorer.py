# Network explorer -- template
# A networkx graph plus a sidebar detail card: click a node (or use ipysigma's
# own search box) and the sidebar shows what it's connected to. Community
# color and centrality-based sizing are both computed with zero Python-side
# graph algorithms (Louvain runs in the browser; PageRank is one line).
# Adapt by swapping `G` for your own graph and `detail()` for your own fields.
#
# Run: uv run --no-sync shiny run template_network_explorer.py
# Data: networkx's bundled Zachary's karate club graph (34 members, 78 ties)
from __future__ import annotations

import networkx as nx
from ipysigma import Sigma
from shiny.express import render, ui
from shinywidgets import render_ipysigma

G = nx.karate_club_graph()
nx.set_node_attributes(G, nx.pagerank(G), "pagerank")

ui.page_opts(title="Network explorer", fillable=True)

with ui.layout_sidebar():
    with ui.sidebar(width=300):
        ui.h5("Detail")
        ui.p(
            "Click a node, or use the search icon inside the graph.",
            class_="text-muted small",
        )

        @render.ui
        def detail():
            raw = graph.read("selected_node")
            if raw is None:
                return ui.p("Nothing selected yet.")
            node = int(raw)
            neighbors = sorted(G.neighbors(node))
            return ui.TagList(
                ui.h6(f"Member {node}"),
                ui.p(f"Club: {G.nodes[node]['club']}"),
                ui.p(f"PageRank: {G.nodes[node]['pagerank']:.3f}"),
                ui.p(f"Connections ({len(neighbors)}): {', '.join(map(str, neighbors))}"),
            )

    with ui.card(full_screen=True):
        ui.card_header("Karate club -- colored by community, sized by PageRank")

        @render_ipysigma
        def graph():
            return Sigma(
                G,
                node_metrics={"community": "louvain"},
                node_color="community",
                node_size="pagerank",
                start_layout=3,
            )
