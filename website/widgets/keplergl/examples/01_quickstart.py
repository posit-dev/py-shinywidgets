import plotly.express as px
from shiny.express import ui
from shinywidgets import render_keplergl

# Montreal car-share station activity: average hours in use per car, and
# the most common peak hour, at 249 stations
carshare = px.data.carshare().rename(
    columns={"centroid_lat": "lat", "centroid_lon": "lon"}
)

ui.page_opts(title="kepler.gl in Shiny", fillable=True)


@render_keplergl
def map():
    return carshare
