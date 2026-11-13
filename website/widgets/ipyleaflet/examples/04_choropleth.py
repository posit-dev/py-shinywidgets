import numpy as np
import ipyleaflet as L
import plotly.express as px
from branca.colormap import linear
from shiny.express import ui
from shinywidgets import render_ipyleaflet

ui.page_opts(title="GeoJSON choropleth", fillable=True)

# plotly's carshare dataset: 249 real car2go pod locations around Montreal,
# aggregated by total usage (car_hours) into a 5x5 grid of cells
pods = px.data.carshare()
lats, lons, hours = pods["centroid_lat"], pods["centroid_lon"], pods["car_hours"]

GRID = 5
lat_edges = np.linspace(lats.min(), lats.max(), GRID + 1)
lon_edges = np.linspace(lons.min(), lons.max(), GRID + 1)
i = np.clip(np.digitize(lats, lat_edges) - 1, 0, GRID - 1)
j = np.clip(np.digitize(lons, lon_edges) - 1, 0, GRID - 1)

features, choro_data = [], {}
for r in range(GRID):
    for c in range(GRID):
        cell_id = f"{r}-{c}"
        mask = (i == r) & (j == c)
        choro_data[cell_id] = float(hours[mask].sum())
        lon0, lon1 = lon_edges[c], lon_edges[c + 1]
        lat0, lat1 = lat_edges[r], lat_edges[r + 1]
        features.append(
            {
                "type": "Feature",
                "id": cell_id,
                "properties": {},
                "geometry": {
                    "type": "Polygon",
                    "coordinates": [
                        [[lon0, lat0], [lon1, lat0], [lon1, lat1], [lon0, lat1], [lon0, lat0]]
                    ],
                },
            }
        )

with ui.card():

    @render_ipyleaflet
    def map():
        m = L.Map(center=(45.52, -73.59), zoom=11)
        m.add(
            L.Choropleth(
                geo_data={"type": "FeatureCollection", "features": features},
                choro_data=choro_data,
                colormap=linear.YlOrRd_06,
                border_color="white",
                style={"fillOpacity": 0.75},
            )
        )
        return m
