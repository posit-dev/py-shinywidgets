from __future__ import annotations

import networkx as nx
import numpy as np
from ipysigma import Sigma
from shiny.express import ui
from shinywidgets import render_ipysigma

# 40 clusters of 500 nodes each (20,000 nodes, ~40k edges): synthetic, since the
# point here is scale rather than a specific real network. Positions are placed
# by hand (one blob per cluster) instead of computed with a force layout, which
# would take too long in pure Python at this size -- and ipysigma skips its own
# random initial layout and the layout-writeback message when `layout=` is given.
rng = np.random.default_rng(0)
N_CLUSTERS, PER_CLUSTER = 40, 500
G = nx.Graph()
layout: dict[int, dict[str, float]] = {}
node_id = 0
for c in range(N_CLUSTERS):
    cx, cy = rng.uniform(-50, 50, 2)
    nodes = list(range(node_id, node_id + PER_CLUSTER))
    for n in nodes:
        G.add_node(n, cluster=str(c))
        angle, radius = rng.uniform(0, 2 * np.pi), rng.uniform(0, 3)
        layout[n] = {"x": cx + radius * np.cos(angle), "y": cy + radius * np.sin(angle)}
    sub = nx.watts_strogatz_graph(PER_CLUSTER, 4, 0.1, seed=c)
    G.add_edges_from((nodes[u], nodes[v]) for u, v in sub.edges())
    node_id += PER_CLUSTER
# a few cross-cluster edges, so the clusters read as one connected network
G.add_edges_from(
    (int(a), int(b)) for a, b in rng.integers(0, node_id, (N_CLUSTERS * 3, 2))
)

ui.page_opts(title="ipysigma scale", fillable=True)

with ui.card(full_screen=True):
    ui.card_header(f"{G.number_of_nodes():,} nodes / {G.number_of_edges():,} edges")

    @render_ipysigma
    def graph():
        return Sigma(
            G,
            layout=layout,
            node_color="cluster",
            default_node_size=2,
            hide_edges_on_move=True,  # keeps panning smooth at this size
        )
