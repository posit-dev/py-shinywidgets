# Title: City point map starter
# A minimal, adaptable starting point: a tile basemap, a handful of points
# sized by a value column, a checkbox filter, and click-for-detail. Swap in
# your own DataFrame and tile source.
# Bucket: template
# Run: cd to the shinywidgets repo root, then
#   uv run --with geoviews shiny run docs/widget-guides/geoviews/gallery/template_city_map.py
# Data: six world cities, hand-entered (lon/lat/population).
import geoviews as gv
import holoviews as hv
import pandas as pd
from shiny import reactive, req
from shiny.express import input, render, ui

from shinywidgets import render_holoviews

hv.extension("bokeh")

cities = pd.DataFrame(
    {
        "city": ["San Francisco", "New York", "London", "Paris", "Tokyo", "Sydney"],
        "lon": [-122.42, -74.01, -0.13, 2.35, 139.69, 151.21],
        "lat": [37.77, 40.71, 51.51, 48.86, 35.69, -33.87],
        "population": [0.87, 8.26, 8.98, 2.16, 13.96, 5.31],
        "region": ["Americas", "Americas", "Europe", "Europe", "Asia", "Oceania"],
    }
)
tap_xy = reactive.value(None)

ui.page_opts(title="City map starter", fillable=True)
ui.input_checkbox_group(
    "regions", "Regions", sorted(cities.region.unique()),
    selected=sorted(cities.region.unique()),
)

with ui.layout_columns():
    with ui.card(full_screen=True):

        @render_holoviews
        def map():
            req(input.regions())
            shown = cities[cities.region.isin(input.regions())]
            points = gv.Points(
                shown, kdims=["lon", "lat"], vdims=["city", "population"]
            ).opts(
                color="firebrick", size=hv.dim("population") * 2 + 6,
                tools=["hover", "tap"],
            )
            hv.streams.Tap(source=points).add_subscriber(lambda x, y: tap_xy.set((x, y)))
            return (gv.tile_sources.OSM * points).opts(responsive=True)

    with ui.card():
        ui.card_header("Clicked city")

        @render.ui
        def detail():
            xy = tap_xy()
            if xy is None:
                return ui.p("Click a city.", class_="text-muted")
            x, y = xy
            shown = cities[cities.region.isin(input.regions())]
            dist = (shown.lon - x) ** 2 + (shown.lat - y) ** 2
            row = shown.loc[dist.idxmin()]
            return ui.TagList(
                ui.h5(row.city), ui.p(f"{row.population:.1f}M people")
            )
