from __future__ import annotations

import networkx as nx
from ipysigma import Sigma
from shiny import reactive, req
from shiny.express import input, ui
from shinywidgets import render_ipysigma

G = nx.karate_club_graph()

ui.page_opts(title="ipysigma carry state", fillable=True)

ui.input_radio_buttons(
    "color_by", "Color nodes by", {"club": "Club", "degree": "Friend count"}
)

with ui.card(full_screen=True):
    # ipysigma only reads its options when a graph is first drawn (there's no
    # Python -> browser trait sync), so changing the color scheme means
    # returning a new Sigma -- which would otherwise reset the pan/zoom the
    # user just set up. Mirror camera_state into a reactive.value and feed it
    # back in, so re-rendering keeps the user's place.
    camera = reactive.value({"x": 0.5, "y": 0.5, "ratio": 1, "angle": 0})

    @reactive.effect
    def _track_camera():
        req(graph.widget)
        camera.set(graph.read("camera_state"))

    @render_ipysigma
    def graph():
        color_by = input.color_by()
        with reactive.isolate():
            # isolate(): reading .widget here (not just camera) would create a
            # circular dependency on this render's own previous output
            cam = camera.get()
        if color_by == "club":
            return Sigma(G, node_color="club", camera_state=cam)
        return Sigma(
            G,
            node_color=dict(G.degree()),
            node_color_gradient=("#dbe9f6", "#08306b"),
            camera_state=cam,
        )
