from __future__ import annotations

import ipyleaflet as L
from shiny import App, render, ui
from shinywidgets import output_widget, render_ipyleaflet, render_leafmap

app_ui = ui.page_fluid(
    ui.output_text("bounds"),
    ui.output_text("zoom"),
    ui.output_text("center"),
    ui.output_text("clicked"),
    ui.output_text("features"),
    ui.output_text("leaf_bounds"),
    ui.card(output_widget("map"), height="450px"),
    ui.card(output_widget("leaf_map"), height="450px"),
)


def server(input, output, session):
    @render_ipyleaflet
    def map():
        m = L.Map(center=(52, 0), zoom=4)
        m.add(L.DrawControl())
        return m

    @render_leafmap
    def leaf_map():
        # leafmap's Map is an ipyleaflet.Map subclass defined in leafmap;
        # mimic it without depending on leafmap (see
        # tests/playwright/render_leafmap)
        LeafmapMap = type("Map", (L.Map,), {"__module__": "leafmap.leafmap"})
        m = LeafmapMap(center=(52, 0), zoom=4)
        m.layout.height = "600px"  # leafmap's default; treated as unset
        return m

    @render.text
    def bounds():
        return str(map.bounds())

    @render.text
    def zoom():
        return str(map.zoom())

    @render.text
    def center():
        return str(map.center())

    @render.text
    def clicked():
        c = map.clicked()
        return "" if c is None else str(c["coordinates"])

    @render.text
    def features():
        return str(len(map.drawn_features()))

    @render.text
    def leaf_bounds():
        return str(leaf_map.bounds())


app = App(app_ui, server)
