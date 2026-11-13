# The same "click a point, see its detail" task on the same 249 real
# car2go pods (Montreal), in ipyleaflet and lonboard. The point: ipyleaflet's
# clicked() reports a *location* (you find the nearest feature yourself);
# lonboard's selected() reports the picked *row* directly. Neither is
# "better" -- ipyleaflet gives per-layer control (clustering, popups,
# drawing); lonboard gives GPU-native picking that also scales past the ~250
# points shown here (see the lonboard guide for the multi-hundred-thousand-
# point case).
# Run: uv run shiny run docs/widget-guides/articles/choosing-a-widget/examples/03_maps_location_vs_feature_pick.py
import geopandas as gpd
import ipyleaflet as L
import plotly.express as px
from lonboard import Map as LonboardMap
from lonboard import ScatterplotLayer
from shiny import req
from shiny.express import render, ui
from shinywidgets import render_ipyleaflet, render_lonboard

ui.page_opts(title="Click-to-detail: ipyleaflet vs. lonboard", fillable=True)

pods = px.data.carshare()  # 249 real car2go pod locations around Montreal

with ui.layout_columns():
    with ui.card(full_screen=True):
        ui.card_header("ipyleaflet: clicked() is a location")

        @render_ipyleaflet
        def map_leaflet():
            m = L.Map(center=(45.52, -73.59), zoom=11)
            markers = [L.CircleMarker(location=(r.centroid_lat, r.centroid_lon), radius=4) for r in pods.itertuples()]
            m.add(L.LayerGroup(layers=markers))
            return m

        @render.ui
        def detail_leaflet():
            c = req(map_leaflet.clicked())
            lat, lng = c["coordinates"]
            d2 = (pods["centroid_lat"] - lat) ** 2 + (pods["centroid_lon"] - lng) ** 2
            row = pods.loc[d2.idxmin()]
            return ui.div(f"Nearest pod #{row.name}: {row['car_hours']:.0f} car-hours")

    with ui.card(full_screen=True):
        ui.card_header("lonboard: selected() is the row")

        @render_lonboard
        def map_lonboard():
            gdf = gpd.GeoDataFrame(
                pods, geometry=gpd.points_from_xy(pods.centroid_lon, pods.centroid_lat)
            )
            layer = ScatterplotLayer.from_geopandas(
                gdf, get_fill_color=[255, 60, 120], radius_min_pixels=5, pickable=True
            )
            return LonboardMap(layer, show_side_panel=False)

        @render.ui
        def detail_lonboard():
            index = req(map_lonboard.selected())
            row = pods.iloc[index]
            return ui.div(f"Picked pod #{row.name}: {row['car_hours']:.0f} car-hours")
