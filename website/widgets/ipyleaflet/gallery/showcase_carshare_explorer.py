# title: Car-share pod explorer
# description: Draw a shape on the map and Shiny answers -- the count, total
#     usage, and busiest-pod shortlist inside it, highlighted on the map
#     without re-rendering it. Also filters by time-of-day and swaps
#     basemaps, both in place.
# bucket: showcase
# run: uv run --no-sync shiny run docs/widget-guides/ipyleaflet/gallery/showcase_carshare_explorer.py
# data: plotly's carshare dataset (249 real car2go pod locations around Montreal)

from __future__ import annotations

import pandas as pd
import plotly.express as px
import ipyleaflet as L
from shapely.geometry import Point, shape
from shiny import reactive
from shiny.express import input, render, ui
from shinywidgets import render_ipyleaflet

ui.page_opts(title="Car-share pod explorer", fillable=True)

PERIODS = ["night", "morning", "afternoon", "evening"]
COLORS = {"night": "#264653", "morning": "#2a9d8f", "afternoon": "#e9c46a", "evening": "#e76f51"}

pods = px.data.carshare()
pods["period"] = pd.cut(pods["peak_hour"], bins=[-1, 5, 11, 17, 23], labels=PERIODS)


def pods_geojson(df: pd.DataFrame) -> dict:
    return {
        "type": "FeatureCollection",
        "features": [
            {
                "type": "Feature",
                "properties": {"period": str(r.period), "car_hours": r.car_hours},
                "geometry": {"type": "Point", "coordinates": [r.centroid_lon, r.centroid_lat]},
            }
            for r in df.itertuples()
        ],
    }


def style_by_period(feature: dict) -> dict:
    return {"radius": 5, "color": COLORS[feature["properties"]["period"]], "fillOpacity": 0.85, "weight": 1}


with ui.sidebar(width=320):
    ui.input_checkbox_group("periods", "Show", PERIODS, selected=PERIODS)
    ui.input_radio_buttons("basemap", "Basemap", ["Light", "Satellite"], selected="Light")
    ui.input_action_button("clear", "Clear drawing", class_="btn-sm mb-2")
    ui.hr()
    ui.markdown("**In view**")

    @render.ui
    def in_view():
        (south, west), (north, east) = map.bounds()
        visible = pods[pods.centroid_lat.between(south, north) & pods.centroid_lon.between(west, east)]
        return f"{len(visible)} of {len(pods)} pods"

    ui.markdown("**Drawn selection**")

    @render.ui
    def stats():
        sel = selected_pods()
        if sel.empty:
            return "Draw a polygon or rectangle to select pods."
        top5 = sel.sort_values("car_hours", ascending=False).head(5)
        return ui.TagList(
            ui.p(f"{len(sel)} pods, {sel['car_hours'].sum():.0f} total car-hours"),
            ui.tags.ol(*[ui.tags.li(f"Pod #{r.Index} ({r.car_hours:.0f} hrs)") for r in top5.itertuples()]),
        )


with ui.card(full_screen=True):

    @render_ipyleaflet
    def map():
        m = L.Map(center=(45.52, -73.59), zoom=11)
        m.add(
            L.GeoJSON(
                data=pods_geojson(pods),
                point_style={"radius": 5},
                style_callback=style_by_period,
                name="pods",
            )
        )
        m.add(
            L.GeoJSON(
                data={"type": "FeatureCollection", "features": []},
                point_style={"radius": 9, "color": "#222", "fillColor": "#ffd166", "fillOpacity": 0.95, "weight": 2},
                name="selected",
            )
        )
        m.add(
            L.DrawControl(
                polygon={"shapeOptions": {"color": "#2a7fff"}},
                rectangle={"shapeOptions": {}},  # {} alone disables the tool
                circle={},
                circlemarker={},
                polyline={},
            )
        )
        m.add(L.LegendControl(COLORS, title="Peak period", position="bottomright"))
        return m


def layer(name: str) -> L.Layer:
    return next(lyr for lyr in map.widget.layers if lyr.name == name)


@reactive.calc
def selected_pods() -> pd.DataFrame:
    feats = map.drawn_features()  # [] until something is drawn
    if not feats:
        return pods.iloc[0:0]
    polys = [shape(f["geometry"]) for f in feats]
    mask = [
        any(poly.contains(Point(lon, lat)) for poly in polys)
        for lat, lon in zip(pods["centroid_lat"], pods["centroid_lon"])
    ]
    return pods[mask]


# Three independent in-place updates, none of which disturbs the map's pan,
# zoom, or the user's drawn shapes.
@reactive.effect
def _filter_by_period():
    layer("pods").data = pods_geojson(pods[pods["period"].isin(input.periods())])


@reactive.effect
def _highlight_selection():
    layer("selected").data = pods_geojson(selected_pods())


@reactive.effect
def _swap_basemap():
    m = map.widget
    old = next(lyr for lyr in m.layers if lyr.base)
    basemap = L.basemaps.Esri.WorldImagery if input.basemap() == "Satellite" else L.basemaps.OpenStreetMap.Mapnik
    new = L.basemap_to_tiles(basemap)
    new.base = True  # basemap_to_tiles() doesn't set this; the next swap's
    # lookup for "the current base layer" depends on it
    m.substitute(old, new)


@reactive.effect
@reactive.event(input.clear)
def _clear_drawing():
    for control in map.widget.controls:
        if isinstance(control, L.DrawControl):
            control.clear()
