import geopandas as gpd
import plotly.express as px
from shiny.express import ui
from shinywidgets import render_keplergl

carshare = px.data.carshare().rename(
    columns={"centroid_lat": "lat", "centroid_lon": "lon"}
)

# A GeoDataFrame works the same way as a plain DataFrame, as long as it's in
# EPSG:4326 (longitude/latitude degrees). kepler.gl doesn't reproject: a
# GeoDataFrame in any other CRS renders in the wrong place with no error.
stations = gpd.GeoDataFrame(
    carshare,
    geometry=gpd.points_from_xy(carshare.lon, carshare.lat),
    crs="EPSG:4326",
)

ui.page_opts(title="GeoDataFrame input", fillable=True)


@render_keplergl
def map():
    return stations
