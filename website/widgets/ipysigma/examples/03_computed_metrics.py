from __future__ import annotations

import networkx as nx
from ipysigma import Sigma
from shiny.express import ui
from shinywidgets import render_ipysigma

G = nx.karate_club_graph()
# PageRank is cheap to compute once in Python and attach as a node attribute;
# ipysigma only computes Louvain community detection itself (node_metrics=).
pagerank = nx.pagerank(G)
nx.set_node_attributes(G, pagerank, "pagerank")

ui.page_opts(title="ipysigma computed metrics", fillable=True)

with ui.card(full_screen=True):
    ui.card_header("Louvain communities (browser-computed), sized by PageRank")

    @render_ipysigma
    def graph():
        return Sigma(
            G,
            # Computed by graphology in the browser, not in Python
            node_metrics={"community": "louvain"},
            node_color="community",
            node_size="pagerank",
        )
