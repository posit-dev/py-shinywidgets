import numpy as np
import pydeck as pdk
import requests
from maplibre import Map, MapOptions
from maplibre.basemaps import Carto
from shiny.express import render, ui
from shinywidgets import render_maplibre

BIKE_RACKS = requests.get(
    "https://raw.githubusercontent.com/visgl/deck.gl-data/master/website/sf-bike-parking.json"
).json()
LNG = np.array([r["COORDINATES"][0] for r in BIKE_RACKS])
LAT = np.array([r["COORDINATES"][1] for r in BIKE_RACKS])

ui.page_opts(fillable=True)

with ui.layout_columns(col_widths=[8, 4]):
    with ui.card(full_screen=True):

        @render_maplibre
        def bike_racks():
            m = Map(MapOptions(style=Carto.POSITRON, center=(-122.4194, 37.7749), zoom=12))
            m.add_deck_layers(
                [
                    pdk.Layer(
                        "ScatterplotLayer",
                        BIKE_RACKS,
                        id="bike-racks",
                        get_position="COORDINATES",
                        get_radius="SPACES",
                        get_fill_color=[255, 140, 0],
                        pickable=True,
                        radius_scale=6,
                        radius_min_pixels=1,
                    )
                ]
            )
            return m

    with ui.card():
        ui.card_header("In view / clicked")

        @render.ui
        def summary():
            vs = bike_racks.read("view_state")
            if vs:
                sw, ne = vs["bounds"]["_sw"], vs["bounds"]["_ne"]
                mask = (LNG >= sw["lng"]) & (LNG <= ne["lng"]) & (LAT >= sw["lat"]) & (LAT <= ne["lat"])
                in_view = f"{int(mask.sum())} of {len(BIKE_RACKS)} racks in view"
            else:
                in_view = f"{len(BIKE_RACKS)} racks (unzoomed)"

            # `clicked` is the map click's lng/lat, not the picked deck.gl
            # object -- find the nearest rack in Python, same workaround the
            # maplibre guide uses for its own `clicked` trait.
            ll = bike_racks.read("clicked")
            if not ll:
                detail = "Click a dot on the map."
            else:
                i = int(np.argmin((LNG - ll["lng"]) ** 2 + (LAT - ll["lat"]) ** 2))
                r = BIKE_RACKS[i]
                detail = f"Nearest rack: {r['ADDRESS']} ({r['SPACES']} spaces)"

            return ui.TagList(ui.tags.p(in_view), ui.tags.p(detail))
