# Title: Map viewport to chart
# Summary: Pan or zoom the map and a bar chart recomputes from whatever is
#     currently in view. The cross-widget "map viewport -> chart" pattern --
#     swap in your own point data and the breakdown you want to chart.
# Bucket: template
# Widgets: ipyleaflet, plotly
# Pattern: map viewport -> chart
# Run: uv run shiny run app.py
# Data: plotly's carshare dataset (249 real car2go pod locations around
#   Montreal, labeled with each pod's peak-use period)
#
# Source: docs/widget-guides/articles/linked-views/examples/06_ipyleaflet_bounds_to_plotly.py

import pandas as pd
import plotly.express as px
import ipyleaflet as L
from shiny.express import ui
from shinywidgets import render_ipyleaflet, render_plotly

ui.page_opts(title="What's in view", fillable=True)

pods = px.data.carshare()
pods["period"] = pd.cut(
    pods["peak_hour"], bins=[-1, 5, 11, 17, 23], labels=["night", "morning", "afternoon", "evening"]
)

with ui.layout_columns(col_widths=[7, 5]):
    with ui.card(full_screen=True):
        ui.card_header("Pan or zoom the map")

        @render_ipyleaflet
        def map():
            m = L.Map(center=(45.52, -73.59), zoom=11)
            markers = [L.Marker(location=(r.centroid_lat, r.centroid_lon)) for r in pods.itertuples()]
            m.add(L.MarkerCluster(markers=markers))
            return m

    with ui.card(full_screen=True):
        ui.card_header("Pods in the current viewport, by peak period")

        @render_plotly
        def in_view():
            (south, west), (north, east) = map.bounds()
            visible = pods[pods.centroid_lat.between(south, north) & pods.centroid_lon.between(west, east)]
            counts = visible["period"].value_counts().reindex(["night", "morning", "afternoon", "evening"]).reset_index()
            counts.columns = ["period", "count"]
            return px.bar(counts, x="period", y="count")
