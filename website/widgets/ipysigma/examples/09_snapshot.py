from __future__ import annotations

import networkx as nx
from shiny import reactive
from shiny.express import input, render, ui
from shinywidgets import render_ipysigma

ui.page_opts(title="ipysigma snapshot", fillable=True)

with ui.layout_columns(col_widths=[7, 5]):
    with ui.card(full_screen=True):
        ui.card_header("Graph")

        @render_ipysigma
        def graph():
            return nx.karate_club_graph()

    with ui.card():
        ui.input_action_button("snap", "Capture PNG")
        ui.card_header("Snapshot")

        @reactive.effect
        @reactive.event(input.snap)
        def _request_snapshot():
            # The only Python -> browser command ipysigma exposes: it answers
            # by setting the `snapshot` trait to a PNG data URL.
            graph.widget.send({"msg": "render_snapshot"})

        @render.ui
        def png():
            data_url = graph.read("snapshot")
            if data_url is None:
                return ui.p("No snapshot yet -- click the button.")
            return ui.img(src=data_url, style="max-width: 100%;")
