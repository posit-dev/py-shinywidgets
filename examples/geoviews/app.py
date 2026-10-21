import geoviews as gv
import holoviews as hv
import pandas as pd
from shiny import App, ui
from shinywidgets import output_widget, render_holoviews

hv.extension("bokeh")

cities = pd.DataFrame(
    {
        "city": ["San Francisco", "New York", "London", "Paris", "Tokyo", "Sydney"],
        "lon": [-122.42, -74.01, -0.13, 2.35, 139.69, 151.21],
        "lat": [37.77, 40.71, 51.51, 48.86, 35.69, -33.87],
        "population": [0.87, 8.26, 8.98, 2.16, 13.96, 5.31],
        "region": ["Americas", "Americas", "Europe", "Europe", "Asia", "Oceania"],
    }
)

app_ui = ui.page_sidebar(
    ui.sidebar(
        ui.input_checkbox_group(
            "regions",
            "Regions",
            sorted(cities["region"].unique()),
            selected=sorted(cities["region"].unique()),
        ),
    ),
    ui.card(
        ui.card_header("Cities (population in millions)"),
        output_widget("map"),
        full_screen=True,
    ),
    title="geoviews with @render_holoviews",
)


def server(input, output, session):
    @render_holoviews
    def map():
        selected = cities[cities["region"].isin(input.regions())]
        points = gv.Points(
            selected, kdims=["lon", "lat"], vdims=["city", "population"]
        ).opts(
            color="firebrick",
            size=hv.dim("population") * 2 + 6,
            tools=["hover"],
        )
        # responsive=True makes the plot fill its container (otherwise
        # holoviews gives it a fixed pixel size)
        return (gv.tile_sources.OSM * points).opts(responsive=True)


app = App(app_ui, server)
