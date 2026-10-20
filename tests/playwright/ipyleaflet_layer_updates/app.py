# Issue #212: updating ipyleaflet layers via reactive effects (without
# re-rendering the map) should work: new layers appear on first update, and
# the layers control keeps listing all layers in its original position.
# Adapted from the issue's repro (an adaptation of the map-distance template).
import ipyleaflet as L
from numpy import random
from shiny import App, reactive, ui
from shinywidgets import output_widget, render_widget

CITIES = {
    "New York": {"latitude": 40.7128, "longitude": -74.0060, "altitude": 33},
    "London": {"latitude": 51.5074, "longitude": -0.1278, "altitude": 36},
    "Paris": {"latitude": 48.8566, "longitude": 2.3522, "altitude": 35},
    "Tokyo": {"latitude": 35.6895, "longitude": 139.6917, "altitude": 44},
    "Sydney": {"latitude": -33.8688, "longitude": 151.2093, "altitude": 39},
}

city_names = sorted(list(CITIES.keys()))

app_ui = ui.page_sidebar(
    ui.sidebar(
        ui.input_selectize(
            "loc1", "Location 1", choices=city_names, selected="New York"
        ),
        ui.input_selectize("loc2", "Location 2", choices=city_names, selected="London"),
        ui.input_action_button("sample", "Sample point"),
    ),
    output_widget("map"),
    title="Location Distance Calculator",
    fillable=True,
    class_="bslib-page-dashboard",
)


def server(input, output, session):
    loc1 = reactive.value()
    loc2 = reactive.value()
    locpoint = reactive.value()

    @reactive.effect
    def _():
        loc1.set(CITIES.get(input.loc1()))
        loc2.set(CITIES.get(input.loc2()))

    @reactive.effect
    @reactive.event(input.sample)
    def _():
        city = random.choice(list(CITIES.keys()), 1)[0]
        locpoint.set(CITIES.get(city))

    @reactive.calc
    def loc1xy():
        return loc1()["latitude"], loc1()["longitude"]

    @reactive.calc
    def loc2xy():
        return loc2()["latitude"], loc2()["longitude"]

    @reactive.calc
    def locpointxy():
        return locpoint()["latitude"], locpoint()["longitude"]

    # Render the map once, then perform partial updates via reactive effects
    @render_widget
    def map():
        esri_sat = L.basemap_to_tiles(L.basemaps.Esri.WorldImagery)
        esri_sat.name = "Esri.WorldImagery"
        esri_sat.base = True

        osm = L.basemap_to_tiles(L.basemaps.OpenStreetMap.Mapnik)
        osm.name = "OpenStreetMap"
        osm.base = True

        m = L.Map(
            zoom=2,
            center=(0, 0),
            scroll_wheel_zoom=True,
            zoom_control=False,
            layers=[esri_sat, osm],
        )

        m.add(L.ZoomControl(position="topright"))
        m.add(L.LayersControl(position="topleft"))

        search_control = L.SearchControl(
            position="topleft",
            url="https://nominatim.openstreetmap.org/search?format=json&q={s}",
            zoom=10,
            auto_collapse=True,
        )

        m.add(search_control)

        return m

    @reactive.effect
    def _():
        update_marker(map.widget, loc1xy(), "loc1")

    @reactive.effect
    def _():
        update_marker(map.widget, loc2xy(), "loc2")

    @reactive.effect
    def _():
        update_marker(map.widget, locpointxy(), "point")

    @reactive.effect
    def _():
        update_line(map.widget, loc1xy(), loc2xy())

    def update_marker(map: L.Map, loc: tuple, name: str):
        remove_layer(map, name)
        map.add(L.Marker(location=loc, draggable=False, name=name, title=name))

    def update_line(map: L.Map, loc1: tuple, loc2: tuple):
        remove_layer(map, "line")
        map.add(L.Polyline(locations=[loc1, loc2], color="blue", weight=2, name="line"))

    def remove_layer(map: L.Map, name: str):
        for layer in map.layers:
            if layer.name == name:
                map.remove(layer)


app = App(app_ui, server)
