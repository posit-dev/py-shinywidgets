import ipyleaflet as L
import plotly.express as px
from shapely.geometry import Point, shape
from shiny.express import render, ui
from shinywidgets import render_ipyleaflet

ui.page_opts(title="Draw a shape, filter the table", fillable=True)

# plotly's carshare dataset: 249 real car2go pod locations around Montreal
pods = px.data.carshare()

with ui.layout_columns(col_widths=[7, 5]):
    with ui.card():

        @render_ipyleaflet
        def map():
            m = L.Map(center=(45.52, -73.59), zoom=11)
            # rectangle={}: an empty dict disables the tool; give it a
            # (possibly empty) shapeOptions to enable it, like the other tools
            m.add(
                L.DrawControl(
                    polygon={"shapeOptions": {"color": "#2a7fff"}},
                    rectangle={"shapeOptions": {}},
                )
            )
            return m

    with ui.card(full_screen=True):
        ui.card_header("Pods inside the drawn shape(s)")

        @render.data_frame
        def inside():
            feats = map.drawn_features()  # [] until something is drawn
            if not feats:
                return pods.iloc[0:0]
            polys = [shape(f["geometry"]) for f in feats]
            mask = [
                any(poly.contains(Point(lon, lat)) for poly in polys)
                for lat, lon in zip(pods["centroid_lat"], pods["centroid_lon"])
            ]
            return render.DataGrid(pods[mask].reset_index(drop=True))
