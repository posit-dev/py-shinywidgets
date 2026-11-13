import ipyleaflet as L
import plotly.express as px
from shiny.express import ui
from shinywidgets import render_ipyleaflet

ui.page_opts(title="Marker clustering", fillable=True)

# plotly's carshare dataset: 249 real car2go pod locations around Montreal
pods = px.data.carshare()

with ui.card():

    @render_ipyleaflet
    def map():
        m = L.Map(center=(45.52, -73.59), zoom=11)
        markers = [L.Marker(location=(r.centroid_lat, r.centroid_lon)) for r in pods.itertuples()]
        m.add(L.MarkerCluster(markers=markers))
        return m
