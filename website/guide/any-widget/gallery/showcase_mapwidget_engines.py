# Showcase: three map engines, one widget, zero dedicated renderer
# mapwidget (https://github.com/opengeos/mapwidget) puts MapLibre GL,
# Leaflet, and OpenLayers behind one 7-trait anywidget API. Swap the engine
# with a dropdown; click the map and Python reads the nearest city via
# map.read(); a style/basemap picker restyles the live widget in place
# (add_call / add_basemap) the moment you change it, and that restyle
# survives an engine swap -- choosing a style, then switching engines, still
# shows the chosen style on the new widget (the queued call is delivered
# once the new widget's comm opens, not dropped; see the guide's "Reacting
# to user interaction" section).
# Run: uv run --no-sync --with mapwidget python -m shiny run showcase_mapwidget_engines.py
# Data: a small built-in list of world cities (lat/lng only, no API keys)
from __future__ import annotations

import math

import mapwidget.leaflet as leaflet
import mapwidget.maplibre as maplibre
import mapwidget.openlayers as openlayers
from shiny import reactive
from shiny.express import input, render, ui
from shinywidgets import render_widget

CITIES = {
    "New York": (40.7128, -74.0060),
    "Tokyo": (35.6762, 139.6503),
    "Nairobi": (-1.2921, 36.8219),
    "Sao Paulo": (-23.5505, -46.6333),
    "Sydney": (-33.8688, 151.2093),
}
MAPLIBRE_STYLES = {
    "Liberty (default)": "https://tiles.openfreemap.org/styles/liberty",
    "Positron (light)": "https://tiles.openfreemap.org/styles/positron",
    "Fiord (dark)": "https://tiles.openfreemap.org/styles/fiord",
}
LEAFLET_BASEMAPS = ["OpenStreetMap", "Esri.WorldImagery", "OpenTopoMap"]


def nearest_city(lat: float, lng: float) -> tuple[str, float]:
    def haversine_km(a: tuple[float, float], b: tuple[float, float]) -> float:
        r = 6371.0
        lat1, lng1, lat2, lng2 = map(math.radians, (*a, *b))
        d_lat, d_lng = lat2 - lat1, lng2 - lng1
        h = (
            math.sin(d_lat / 2) ** 2
            + math.cos(lat1) * math.cos(lat2) * math.sin(d_lng / 2) ** 2
        )
        return 2 * r * math.asin(math.sqrt(h))

    name, (clat, clng) = min(CITIES.items(), key=lambda kv: haversine_km((lat, lng), kv[1]))
    return name, haversine_km((lat, lng), (clat, clng))


ui.page_opts(title="Three engines, one widget (mapwidget)", fillable=True)

with ui.sidebar(width=280):
    ui.input_select("engine", "Engine", ["maplibre", "leaflet", "openlayers"])
    ui.input_select("style", "MapLibre style", list(MAPLIBRE_STYLES))
    ui.input_select("basemap", "Leaflet basemap", LEAFLET_BASEMAPS)
    ui.input_select("city", "Fly to (MapLibre only)", list(CITIES))
    ui.input_action_button("flyto", "Fly")

    @render.ui
    def info():
        zoom = mw.read("zoom")
        lat, lng = mw.read("clicked_latlng")
        if lat is None:
            click_line = "click the map to find the nearest city"
        else:
            name, dist = nearest_city(lat, lng)
            click_line = f"nearest: {name} ({dist:,.0f} km away)"
        return ui.markdown(f"**zoom:** {zoom:.1f}\n\n{click_line}")


with ui.card(full_screen=True):

    @render_widget
    def mw():
        # The engine choice needs a different ipywidgets class, so this
        # re-renders (a fresh widget, new comm) on engine change. The
        # style/basemap/fly-to effects below are in-place updates on
        # whichever widget is live -- reading `mw.widget` (rather than
        # closing over one captured instance) is what makes them target the
        # new widget after a swap. The queued call for that swap itself is
        # delivered once the new widget's comm opens, not dropped, so the
        # chosen style/basemap carries over automatically.
        if input.engine() == "leaflet":
            return leaflet.Map(center=[40.7128, -74.0060], zoom=4)
        if input.engine() == "openlayers":
            return openlayers.Map(center=[40.7128, -74.0060], zoom=4)
        return maplibre.Map(center=[40.7128, -74.0060], zoom=4)

    # add_call()/add_basemap() run from an effect, same as any other
    # in-place update -- see 08_third_party_mapwidget.py.
    @reactive.effect
    def _restyle_maplibre():
        if input.engine() == "maplibre":
            mw.widget.add_call("setStyle", [MAPLIBRE_STYLES[input.style()]])

    @reactive.effect
    def _restyle_leaflet():
        if input.engine() == "leaflet":
            mw.widget.add_basemap(input.basemap())

    @reactive.effect
    @reactive.event(input.flyto)
    def _fly():
        if input.engine() == "maplibre":
            lat, lng = CITIES[input.city()]
            mw.widget.add_call("flyTo", [{"center": [lng, lat], "zoom": 5}])
