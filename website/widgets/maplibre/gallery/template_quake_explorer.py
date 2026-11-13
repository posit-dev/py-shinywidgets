# Quake explorer -- filter, click-to-detail and a viewport count, in one small map.
# bucket: template
# run: uv run shiny run docs/widget-guides/maplibre/gallery/template_quake_explorer.py
# data: maplibre's own earthquakes.geojson tutorial dataset (~6,100 points, no API key)
import numpy as np
import requests
from maplibre import Layer, LayerType, Map, MapOptions
from maplibre.basemaps import Carto
from maplibre.sources import GeoJSONSource
from shiny import reactive
from shiny.express import input, render, ui
from shinywidgets import render_maplibre

EARTHQUAKES = requests.get(
    "https://maplibre.org/maplibre-gl-js/docs/assets/earthquakes.geojson"
).json()
LNG = np.array([f["geometry"]["coordinates"][0] for f in EARTHQUAKES["features"]])
LAT = np.array([f["geometry"]["coordinates"][1] for f in EARTHQUAKES["features"]])
MAG = np.array([f["properties"]["mag"] for f in EARTHQUAKES["features"]])

ui.page_opts(title="Quake explorer", fillable=True)

with ui.sidebar():
    ui.input_slider("min_mag", "Minimum magnitude", 0, 8, 4, step=0.5)
    ui.markdown("Pan, zoom and click a dot. The filter restyles in place --- the camera never resets.")

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
                    paint={
                        "circle-radius": ["interpolate", ["linear"], ["get", "mag"], 0, 2, 8, 14],
                        "circle-color": ["interpolate", ["linear"], ["get", "mag"], 0, "#ffffb2", 8, "#bd0026"],
                        "circle-stroke-color": "white",
                        "circle-stroke-width": 0.5,
                    },
                )
            )
            return m

    with ui.card():
        ui.card_header("On screen")

        @render.text
        def in_view():
            vs = quakes.view_state()
            mask = visible_mask(vs) & (MAG >= input.min_mag())
            return f"{int(mask.sum())} of {len(MAG)} earthquakes"

        ui.card_header("Clicked")

        @render.ui
        def detail():
            ll = quakes.clicked()
            if ll is None:
                return "Click a dot."
            i = int(np.argmin((LNG - ll["lng"]) ** 2 + (LAT - ll["lat"]) ** 2))
            return f"Nearest quake: magnitude {MAG[i]}"


@reactive.effect
def _filter():
    quakes.widget.set_filter("quakes-circle", [">=", ["get", "mag"], input.min_mag()])


def visible_mask(vs: dict) -> np.ndarray:
    sw, ne = vs["bounds"]["_sw"], vs["bounds"]["_ne"]
    return (LNG >= sw["lng"]) & (LNG <= ne["lng"]) & (LAT >= sw["lat"]) & (LAT <= ne["lat"])
