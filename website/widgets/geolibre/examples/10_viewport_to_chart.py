from __future__ import annotations

from geolibre import Map
from matplotlib.figure import Figure
from shiny import render, req
from shiny.express import ui

from shinywidgets import render_geolibre

ui.page_opts(title="Viewport -> visible-cities chart", fillable=True)

# name, lng, lat, population (millions)
CITIES = [
    ("New York", -74.0, 40.7, 8.48),
    ("Los Angeles", -118.2, 34.0, 3.88),
    ("Chicago", -87.6, 41.9, 2.72),
    ("Houston", -95.4, 29.8, 2.31),
    ("Phoenix", -112.1, 33.4, 1.65),
    ("Denver", -104.99, 39.74, 0.72),
    ("Seattle", -122.33, 47.6, 0.74),
    ("Miami", -80.19, 25.76, 0.44),
]

with ui.layout_columns(col_widths=[7, 5]):
    with ui.card(full_screen=True):

        @render_geolibre
        def map():
            return Map(center=(-98.5, 39.8), zoom=3.5)

    with ui.card():
        ui.card_header("Cities currently on screen")

        @render.plot
        def visible_cities():
            # "bbox" fills in once the browser's first sync lands, a moment
            # after the app boots -- req() cancels the output until then.
            bbox = map.read("project")["mapView"].get("bbox")
            west, south, east, north = req(bbox)
            shown = [
                (name, pop)
                for name, lng, lat, pop in CITIES
                if west <= lng <= east and south <= lat <= north
            ]
            fig = Figure(figsize=(5, 4), layout="tight")
            ax = fig.subplots()
            if shown:
                names, pops = zip(*sorted(shown, key=lambda c: c[1]))
                ax.barh(names, pops, color="#2a6fdb")
            ax.set_xlabel("Population (millions)")
            return fig
