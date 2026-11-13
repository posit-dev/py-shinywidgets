# pydeck -> maplibre migration template: SF bike-parking racks as a pdk.Layer
# rendered on a reactive maplibre map.
# bucket: template
# run: uv run --with pydeck --with "maplibre[anywidget]" shiny run template_bike_racks.py
# data: visgl/deck.gl-data's public sf-bike-parking.json (pydeck's own ScatterplotLayer
# tutorial dataset, no API key)
import numpy as np
import pydeck as pdk
import requests
from maplibre import Map, MapOptions
from maplibre.basemaps import Carto
from shiny import reactive
from shiny.express import input, render, ui
from shinywidgets import render_maplibre

RACKS = requests.get(
    "https://raw.githubusercontent.com/visgl/deck.gl-data/master/website/sf-bike-parking.json"
).json()
LNG = np.array([r["COORDINATES"][0] for r in RACKS])
LAT = np.array([r["COORDINATES"][1] for r in RACKS])
TOOLTIP = {"racks": "{{ADDRESS}}: {{SPACES}} spaces"}

ui.page_opts(title="SF bike racks: a pydeck -> maplibre migration", fillable=True)
ui.input_slider("radius_scale", "Radius scale", 1, 20, 6)

with ui.layout_columns(col_widths=[8, 4]):
    with ui.card(full_screen=True):

        @render_maplibre
        def racks():
            m = Map(MapOptions(style=Carto.POSITRON, center=(-122.4194, 37.7749), zoom=12))
            # Filled (and restyled in place) by the effect below -- the data
            # crosses the wire once, at start-up.
            m.add_deck_layers([], tooltip=TOOLTIP)
            return m

        @reactive.effect
        def _restyle():
            racks.widget.set_deck_layers([scatter_layer()], tooltip=TOOLTIP)

    with ui.card():
        ui.card_header("In view / clicked")

        @render.ui
        def summary():
            vs = racks.read("view_state")
            if vs:
                sw, ne = vs["bounds"]["_sw"], vs["bounds"]["_ne"]
                mask = (LNG >= sw["lng"]) & (LNG <= ne["lng"]) & (LAT >= sw["lat"]) & (LAT <= ne["lat"])
                in_view = f"{int(mask.sum())} of {len(RACKS)} racks in view"
            else:
                in_view = f"{len(RACKS)} racks (unzoomed)"

            # `clicked` is the map click's lng/lat, not the picked deck.gl
            # object -- find the nearest rack in Python.
            ll = racks.read("clicked")
            if not ll:
                detail = "Click a dot on the map."
            else:
                i = int(np.argmin((LNG - ll["lng"]) ** 2 + (LAT - ll["lat"]) ** 2))
                r = RACKS[i]
                detail = f"Nearest rack: {r['ADDRESS']} ({r['SPACES']} spaces)"

            return ui.TagList(ui.tags.p(in_view), ui.tags.p(detail))


def scatter_layer() -> pdk.Layer:
    return pdk.Layer(
        "ScatterplotLayer",
        RACKS,
        id="racks",
        get_position="COORDINATES",
        get_radius="SPACES",
        get_fill_color=[255, 140, 0],
        pickable=True,
        opacity=0.8,
        stroked=True,
        filled=True,
        radius_scale=input.radius_scale(),
        radius_min_pixels=1,
        radius_max_pixels=100,
        line_width_min_pixels=1,
    )
