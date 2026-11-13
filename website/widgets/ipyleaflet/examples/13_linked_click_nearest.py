import plotly.express as px
import ipyleaflet as L
from shiny.express import render, ui
from shinywidgets import render_ipyleaflet

ui.page_opts(title="Click for the nearest pod", fillable=True)

# plotly's carshare dataset: 249 real car2go pod locations around Montreal
pods = px.data.carshare()

with ui.layout_columns(col_widths=[8, 4]):
    with ui.card():

        @render_ipyleaflet
        def map():
            m = L.Map(center=(45.52, -73.59), zoom=11)
            markers = [L.Marker(location=(r.centroid_lat, r.centroid_lon)) for r in pods.itertuples()]
            m.add(L.MarkerCluster(markers=markers))
            return m

    with ui.card():
        ui.card_header("Nearest pod to your last click")

        @render.ui
        def nearest():
            c = map.clicked()
            if c is None:
                return "Click the map."
            lat, lng = c["coordinates"]
            d2 = (pods["centroid_lat"] - lat) ** 2 + (pods["centroid_lon"] - lng) ** 2
            row = pods.loc[d2.idxmin()]
            return ui.div(ui.h5(f"Pod #{row.name}"), f"{row['car_hours']:.0f} car-hours")
