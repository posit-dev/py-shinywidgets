import matplotlib.pyplot as plt
import numpy as np
import requests
from maplibre import Layer, LayerType, Map, MapOptions
from maplibre.basemaps import Carto
from maplibre.sources import GeoJSONSource
from shiny.express import render, ui
from shinywidgets import render_maplibre

EARTHQUAKES = requests.get(
    "https://maplibre.org/maplibre-gl-js/docs/assets/earthquakes.geojson"
).json()
LNG = np.array([f["geometry"]["coordinates"][0] for f in EARTHQUAKES["features"]])
LAT = np.array([f["geometry"]["coordinates"][1] for f in EARTHQUAKES["features"]])
MAG = np.array([f["properties"]["mag"] for f in EARTHQUAKES["features"]])

ui.page_opts(fillable=True)

with ui.layout_columns(col_widths=[8, 4]):
    with ui.card(full_screen=True):

        @render_maplibre
        def quakes():
            m = Map(MapOptions(style=Carto.DARK_MATTER, center=(0, 20), zoom=1.2))
            m.add_source("quakes", GeoJSONSource(data=EARTHQUAKES))
            m.add_layer(
                Layer(
                    id="quakes-circle",
                    type=LayerType.CIRCLE,
                    source="quakes",
                    paint={"circle-radius": 2, "circle-color": "#fd8d3c", "circle-opacity": 0.6},
                )
            )
            return m

    with ui.card():
        ui.card_header("What's on screen")

        @render.plot
        def visible_mags():
            vs = quakes.view_state()
            sw, ne = vs["bounds"]["_sw"], vs["bounds"]["_ne"]
            mask = (LNG >= sw["lng"]) & (LNG <= ne["lng"]) & (LAT >= sw["lat"]) & (LAT <= ne["lat"])
            fig, ax = plt.subplots()
            ax.hist(MAG[mask], bins=np.arange(0, 9, 0.5))
            ax.set_title(f"{int(mask.sum())} earthquakes in view")
            ax.set_xlabel("Magnitude")
            return fig
