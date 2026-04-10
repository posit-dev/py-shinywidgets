from __future__ import annotations

import ipyleaflet as L
from shiny import App, reactive, ui
from shinywidgets import output_widget, render_widget

ROUTES = [
    [(37.7749, -122.4194), (37.8044, -122.2712)],
    [(37.8044, -122.2712), (37.6879, -122.4702)],
    [(37.6879, -122.4702), (37.7749, -122.4194)],
]

app_ui = ui.page_fluid(
    ui.input_action_button("update_route", "Update route"),
    ui.input_action_button("toggle_sample", "Toggle sample"),
    output_widget("map"),
)


def server(input, output, session):
    esri_sat = L.basemap_to_tiles(L.basemaps.Esri.WorldImagery)
    esri_sat.name = "Esri.WorldImagery"
    esri_sat.base = True

    osm = L.basemap_to_tiles(L.basemaps.OpenStreetMap.Mapnik)
    osm.name = "OpenStreetMap"
    osm.base = True

    start_icon = L.DivIcon(
        html="""
        <div
          class="endpoint-marker endpoint-start"
          style="width: 12px; height: 12px; border-radius: 50%;
                 background: #e74c3c; border: 2px solid white;">
        </div>
        """,
        icon_size=(16, 16),
        icon_anchor=(8, 8),
    )

    end_icon = L.DivIcon(
        html="""
        <div
          class="endpoint-marker endpoint-end"
          style="width: 12px; height: 12px; border-radius: 50%;
                 background: #3498db; border: 2px solid white;">
        </div>
        """,
        icon_size=(16, 16),
        icon_anchor=(8, 8),
    )

    sample_icon = L.DivIcon(
        html="""
        <div
          class="sample-point"
          style="width: 12px; height: 12px; border-radius: 50%;
                 background: #2ecc71; border: 2px solid white;">
        </div>
        """,
        icon_size=(16, 16),
        icon_anchor=(8, 8),
    )

    map_widget: L.Map | None = None
    route_layers: list[L.Layer] = []
    sample_marker = L.Marker(location=(37.7600, -122.4400), icon=sample_icon, name="Sample")
    sample_visible = False
    route_index = 0

    def build_route_layers(route_points: list[tuple[float, float]]) -> list[L.Layer]:
        start, end = route_points[0], route_points[-1]
        return [
            L.Marker(location=start, icon=start_icon, name="Start"),
            L.Marker(location=end, icon=end_icon, name="End"),
            L.Polyline(locations=route_points, color="#ff6600", weight=5, name="Route"),
        ]

    def set_route(route_points: list[tuple[float, float]]) -> None:
        nonlocal route_layers
        if map_widget is None:
            return
        for layer in route_layers:
            map.widget.remove_layer(layer)
        route_layers = build_route_layers(route_points)
        for layer in route_layers:
            map.widget.add_layer(layer)

    @reactive.effect
    @reactive.event(input.update_route)
    def _update_route():
        nonlocal route_index
        if map_widget is None:
            return
        route_index = (route_index + 1) % len(ROUTES)
        set_route(ROUTES[route_index])

    @reactive.effect
    @reactive.event(input.toggle_sample)
    def _toggle_sample():
        nonlocal sample_visible
        if map_widget is None:
            return
        if sample_visible:
            map.widget.remove_layer(sample_marker)
            sample_visible = False
        else:
            map.widget.add_layer(sample_marker)
            sample_visible = True

    @render_widget
    def map():
        nonlocal map_widget
        if map_widget is None:
            map_widget = L.Map(
                center=(37.7749, -122.4194),
                zoom=10,
                scroll_wheel_zoom=True,
                zoom_control=False,
                layers=[esri_sat, osm],
            )
            map_widget.add_control(L.ZoomControl(position="topright"))
            map_widget.add_control(L.LayersControl(position="topleft"))
            map_widget.add_control(
                L.SearchControl(
                    url="https://nominatim.openstreetmap.org/search?format=json&q={s}",
                    position="topleft",
                    zoom=12,
                    auto_collapse=True,
                ),
            )
            route_layers.extend(build_route_layers(ROUTES[route_index]))
            for layer in route_layers:
                map_widget.add_layer(layer)
        return map_widget


app = App(app_ui, server)
