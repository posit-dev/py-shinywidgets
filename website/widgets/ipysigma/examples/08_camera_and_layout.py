from __future__ import annotations

import networkx as nx
from ipysigma import Sigma
from shiny.express import render, ui
from shinywidgets import render_ipysigma

G = nx.karate_club_graph()

ui.page_opts(title="ipysigma camera and layout", fillable=True)

with ui.layout_columns(col_widths=[8, 4]):
    with ui.card(full_screen=True):
        ui.card_header("Drag to pan, scroll to zoom, or let the layout settle")

        @render_ipysigma
        def graph():
            # Runs ForceAtlas2 for 3 seconds, then writes the converged
            # positions back to the `layout` trait.
            return Sigma(G, start_layout=3)

    with ui.card():
        ui.card_header("What Python sees")

        @render.code
        def state():
            camera = graph.read("camera_state")
            layout = graph.read("layout")
            n_positioned = 0 if layout is None else len(layout)
            camera_lines = "\n".join(f"  {k}: {v:.3g}" for k, v in camera.items())
            return f"camera_state:\n{camera_lines}\nlayout: {n_positioned} node positions"
