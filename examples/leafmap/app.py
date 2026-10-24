import leafmap.leafmap as leafmap
import numpy as np
from shiny import reactive, render, req
from shiny.express import input, ui

from shinywidgets import reactive_read, render_leafmap

# A few hundred synthetic points around Seattle
rng = np.random.default_rng(1)
N = 400
lat = 47.6 + 0.15 * rng.standard_normal(N)
lon = -122.33 + 0.2 * rng.standard_normal(N)
value = rng.integers(1, 100, N)

geojson = {
    "type": "FeatureCollection",
    "features": [
        {
            "type": "Feature",
            "geometry": {"type": "Point", "coordinates": [float(x), float(y)]},
            "properties": {"value": int(v)},
        }
        for x, y, v in zip(lon, lat, value)
    ],
}

ui.page_opts(title="leafmap demo", fillable=True)

with ui.sidebar():
    ui.input_slider("zoom", "Map zoom level", value=10, min=8, max=14)
    ui.input_slider("min_value", "Minimum value", value=1, min=1, max=100)
    ui.hr()


@render_leafmap
def lmap():
    # leafmap's Map is an ipyleaflet map, and fills its output by default
    m = leafmap.Map(center=(47.6, -122.33), zoom=10)
    m.add_basemap("Esri.WorldTopoMap")
    m.add_geojson(
        geojson,
        layer_name="points",
        point_style={
            "radius": 4,
            "fillColor": "#e4572e",
            "color": "#ffffff",
            "weight": 1,
            "fillOpacity": 0.85,
        },
    )
    return m


@reactive.effect
def _():
    lmap.widget.zoom = input.zoom()


# Filter in place by replacing the layer's data (no re-render, so the map keeps
# its view)
@reactive.effect
def _():
    m = lmap.widget
    req(m is not None)
    with reactive.isolate():
        layer = m.layers[-1]
    threshold = input.min_value()
    with reactive.isolate():
        layer.data = {
            "type": "FeatureCollection",
            "features": [
                f for f in geojson["features"] if f["properties"]["value"] >= threshold
            ],
        }


# The visible map area is an input: react to panning/zooming the map
@render.text
def in_view():
    b = reactive_read(lmap.widget, "bounds")
    req(b)
    (south, west), (north, east) = b
    n = sum(1 for f in geojson["features"] if south <= f["geometry"]["coordinates"][1] <= north)
    return f"{n} of {len(geojson['features'])} points are in view"
