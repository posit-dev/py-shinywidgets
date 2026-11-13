import plotly.express as px
from shiny.express import render, ui
from shinywidgets import render_keplergl

carshare = px.data.carshare().rename(
    columns={"centroid_lat": "lat", "centroid_lon": "lon"}
)

ui.page_opts(title="Reading kepler.gl's config", fillable=True)

with ui.layout_columns(col_widths=[8, 4]):
    with ui.card(full_screen=True):

        @render_keplergl
        def map():
            return carshare

    with ui.card():
        ui.card_header("Map view (from config.mapState)")

        @render.code
        def view_state():
            config = map.read("config")
            state = config.get("config", {}).get("mapState", {})
            if not state:
                return "Waiting for the map to load..."
            return (
                f"lat:     {state['latitude']:.3f}\n"
                f"lon:     {state['longitude']:.3f}\n"
                f"zoom:    {state['zoom']:.2f}\n"
                f"pitch:   {state['pitch']:.0f}\n"
                f"bearing: {state['bearing']:.0f}"
            )
