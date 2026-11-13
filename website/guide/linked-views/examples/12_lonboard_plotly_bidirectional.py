# Two-way linking without loops, across two different widget libraries.
#
# lonboard and plotly have no shared "selection" trait to mirror directly
# (unlike two jscatter plots -- see 11_jscatter_bidirectional.py), so instead
# of wiring the widgets to each other, both point at ONE shared
# `reactive.value`: whichever widget was clicked writes the row index there
# (guarded by an equality check + reactive.isolate() so the write doesn't
# depend on itself), and two more effects fan that single value out to both
# widgets' in-place highlight. Neither widget ever reads the other's
# accessor, so there is no cycle to break -- the broker IS the loop-breaker.
import geopandas as gpd
import numpy as np
import plotly.express as px
from lonboard import Map, ScatterplotLayer
from shiny import reactive
from shiny.express import ui
from shinywidgets import render_lonboard, render_plotly

pods = px.data.carshare().reset_index(drop=True)
GDF = gpd.GeoDataFrame(
    pods, geometry=gpd.points_from_xy(pods["centroid_lon"], pods["centroid_lat"]), crs="EPSG:4326"
)
DIM, BRIGHT = (120, 140, 200, 140), (230, 30, 30, 255)

ui.page_opts(title="Two-way linking without loops", fillable=True)

selected = reactive.value(None)

with ui.layout_columns():
    with ui.card(full_screen=True):
        ui.card_header("lonboard: click a pod")

        @render_lonboard
        def geo():
            layer = ScatterplotLayer.from_geopandas(
                GDF,
                get_fill_color=np.array([DIM] * len(pods), dtype=np.uint8),
                radius_min_pixels=5,
                pickable=True,
            )
            # The plotly panel already shows which pod is selected
            return Map(layer, show_side_panel=False)

    with ui.card(full_screen=True):
        ui.card_header("plotly: click the same pod")

        @render_plotly
        def chart():
            fig = px.scatter(pods, x="centroid_lon", y="centroid_lat")
            fig.update_traces(marker_color="#9ecae1")
            fig.update_layout(margin=dict(l=10, r=10, t=10, b=10))
            return fig


@reactive.effect
def _map_sets_selection():
    idx = geo.selected()
    if idx is None:
        return
    with reactive.isolate():
        if selected() != idx:
            selected.set(idx)


@reactive.effect
def _chart_sets_selection():
    pts = chart.clicked()
    if pts is None:
        return
    idx = int(pts["point_index"].iloc[0])
    with reactive.isolate():
        if selected() != idx:
            selected.set(idx)


@reactive.effect
def _highlight_map():
    idx = selected()
    colors = np.array([BRIGHT if i == idx else DIM for i in range(len(pods))], dtype=np.uint8)
    with reactive.isolate():
        w = geo.widget
        if w is not None:
            w.layers[0].get_fill_color = colors


@reactive.effect
def _highlight_chart():
    idx = selected()
    colors = ["#e41a1c" if i == idx else "#9ecae1" for i in range(len(pods))]
    with reactive.isolate():
        w = chart.widget
        if w is not None:
            w.data[0].marker.color = colors
