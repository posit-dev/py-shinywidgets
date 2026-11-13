# Title: Spatial explorer
# Summary: Clustered markers, a live "in view" count, and click-to-detail --
#     a clean starting point for any point dataset.
# Bucket: template
# Widgets: ipyleaflet
# Pattern: viewport -> live count, click -> detail
# Run: uv run shiny run app.py
# Data: plotly's carshare dataset (249 real car2go pod locations around Montreal)
#
# Source: docs/widget-guides/ipyleaflet/gallery/template_spatial_explorer.py

import plotly.express as px
import ipyleaflet as L
from shiny.express import render, ui
from shinywidgets import render_ipyleaflet

ui.page_opts(title="Spatial explorer", fillable=True)

pods = px.data.carshare()

with ui.layout_columns(col_widths=[8, 4], fill=True):
    with ui.card(full_screen=True):

        @render_ipyleaflet
        def map():
            m = L.Map(center=(45.52, -73.59), zoom=11)
            markers = [L.Marker(location=(r.centroid_lat, r.centroid_lon)) for r in pods.itertuples()]
            m.add(L.MarkerCluster(markers=markers))
            return m

    with ui.layout_columns(col_widths=12, row_heights=[1, 2]):
        with ui.card():
            ui.card_header("In view")

            @render.ui
            def in_view_count():
                (south, west), (north, east) = map.bounds()
                visible = pods[pods.centroid_lat.between(south, north) & pods.centroid_lon.between(west, east)]
                return ui.h2(f"{len(visible)} / {len(pods)}")

        with ui.card():
            ui.card_header("Nearest to your last click")

            @render.ui
            def nearest():
                c = map.clicked()
                if c is None:
                    return "Click the map to pick a pod."
                lat, lng = c["coordinates"]
                d2 = (pods["centroid_lat"] - lat) ** 2 + (pods["centroid_lon"] - lng) ** 2
                row = pods.loc[d2.idxmin()]
                return ui.div(ui.h5(f"Pod #{row.name}"), f"{row['car_hours']:.0f} car-hours")
