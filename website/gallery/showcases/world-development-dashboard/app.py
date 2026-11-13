# Title: World development dashboard
# Bucket: showcase
# Description: A GDP-per-capita choropleth with a population-scaled city
#   layer on top. Styling restyles in place (no re-send of the 177 country
#   polygons or 243 cities); the sidebar's "cities in view" stat and the
#   detail card both come from lonboard's reactive accessors.
# Run: shiny run app.py
# Data: Natural Earth 110m countries + populated places (public domain),
#   fetched at startup from a GitHub mirror.

import math

import geopandas as gpd
import matplotlib.pyplot as plt
import numpy as np
from lonboard import Map, PolygonLayer, ScatterplotLayer
from lonboard.colormap import apply_continuous_cmap
from shapely.geometry import box
from shiny import reactive, req
from shiny.express import input, render, ui

from shinywidgets import render_lonboard

ui.page_opts(title="World development dashboard", fillable=True)

COUNTRIES_URL = "https://raw.githubusercontent.com/nvkelso/natural-earth-vector/master/geojson/ne_110m_admin_0_countries.geojson"
CITIES_URL = "https://raw.githubusercontent.com/nvkelso/natural-earth-vector/master/geojson/ne_110m_populated_places.geojson"

# Reported once by a tiny ResizeObserver, used to turn view_state (center +
# zoom) into an exact lng/lat viewport box -- lonboard has no bounds trait.
ui.head_content(
    ui.tags.script("""
    $(document).on("shiny:connected", function() {
      function send() {
        var el = document.querySelector("#map");
        if (el) Shiny.setInputValue("map_px", [el.clientWidth, el.clientHeight]);
      }
      new ResizeObserver(send).observe(document.body);
      setTimeout(send, 300);
    });
    """)
)

with ui.sidebar(width=320):
    ui.input_slider("city_radius", "City point radius (px)", 2, 14, 5)
    ui.input_switch("by_pop", "Size cities by population", True)
    ui.input_select("fly_to", "Fly to", ["-"] + ["Tokyo", "Lagos", "São Paulo", "Paris"])
    ui.hr()
    ui.h6("Currently in view")

    @render.ui
    def in_view_stats():
        vs = map.view_state()
        width, height = req(input.map_px())
        bounds = view_bounds(vs.longitude, vs.latitude, vs.zoom, width, height)
        visible = cities()[cities().geometry.within(box(*bounds))]
        total_pop = int(visible["POP_MAX"].sum())
        return ui.TagList(
            ui.p(f"{len(visible)} cities", class_="mb-1"),
            ui.p(f"{total_pop:,} people", class_="mb-0 text-muted small"),
        )

    ui.hr()
    ui.h6("Selected city")

    @render.ui
    def detail():
        index = req(map.selected())
        row = cities().iloc[index]
        return ui.TagList(
            ui.strong(row["NAME"]),
            ui.p(row["ADM0NAME"], class_="mb-0 text-muted small"),
        )


with ui.card(full_screen=True):

    @render_lonboard
    def map():
        gdp_per_capita = countries()["GDP_MD"] * 1e6 / countries()["POP_EST"]
        country_layer = PolygonLayer.from_geopandas(
            countries(),
            get_fill_color=apply_continuous_cmap(
                gdp_per_capita.rank(pct=True).to_numpy(), plt.get_cmap("YlGnBu")
            ),
            get_line_color=[255, 255, 255],
            line_width_min_pixels=0.5,
            opacity=0.9,
        )
        with reactive.isolate():
            style = city_style()
        city_layer = ScatterplotLayer.from_geopandas(
            cities(), pickable=True, auto_highlight=True, **style
        )
        return Map([country_layer, city_layer], show_side_panel=False)


@reactive.calc
def countries() -> gpd.GeoDataFrame:
    return gpd.read_file(COUNTRIES_URL)


@reactive.calc
def cities() -> gpd.GeoDataFrame:
    return gpd.read_file(CITIES_URL)


def city_style() -> dict:
    if input.by_pop():
        radius = np.sqrt(cities()["POP_MAX"].to_numpy()) * 0.002 + input.city_radius()
    else:
        radius = input.city_radius()
    return {"get_radius": radius, "radius_units": "pixels", "get_fill_color": [255, 70, 130]}


@reactive.effect
@reactive.event(input.city_radius, input.by_pop, ignore_init=True)
def _restyle_cities():
    # In-place restyle: only the layer's style traits are re-sent, not the
    # 243 points, so zoom/selection/camera are untouched
    layer = map.widget.layers[1]
    style = city_style()
    layer.get_radius = style["get_radius"]
    layer.radius_units = style["radius_units"]


FLY_TO = {
    "Tokyo": (139.75, 35.68, 9),
    "Lagos": (3.38, 6.45, 9),
    "São Paulo": (-46.63, -23.55, 9),
    "Paris": (2.33, 48.87, 9),
}


@reactive.effect
@reactive.event(input.fly_to, ignore_init=True)
def _fly_to_city():
    if input.fly_to() == "-":
        return
    lon, lat, zoom = FLY_TO[input.fly_to()]
    map.widget.fly_to(longitude=lon, latitude=lat, zoom=zoom, duration=1200)


def inv_merc(y: float) -> float:
    return math.degrees(2 * math.atan(math.exp(y)) - math.pi / 2)


def view_bounds(
    lon: float, lat: float, zoom: float, width: float, height: float
) -> tuple[float, float, float, float]:
    """(minx, miny, maxx, maxy) of a Web Mercator viewport (512px tiles)."""
    world_px = 512 * 2**zoom
    half_w = (width / 2) * 360 / world_px
    half_h = (height / 2) * (2 * math.pi) / world_px
    m = math.log(math.tan(math.pi / 4 + math.radians(lat) / 2))
    return (lon - half_w, inv_merc(m - half_h), lon + half_w, inv_merc(m + half_h))
