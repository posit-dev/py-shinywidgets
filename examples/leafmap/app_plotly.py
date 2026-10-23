from leafmap.plotlymap import Map
from shiny import reactive
from shiny.express import input, ui
from shinywidgets import render_leafmap

ui.page_opts(title="leafmap with Plotly", fillable=True)

with ui.sidebar():
    ui.input_slider("zoom", "Map zoom", min=7, max=12, value=9)
    ui.input_select("color", "Marker color", choices=["red", "blue", "green"])


@render_leafmap
def lmap() -> Map:
    m = Map(center=(37.6, -122.4), zoom=9, basemap="open-street-map")
    m.add_scattermapbox(
        lat=[37.6, 37.7],
        lon=[-122.4, -122.5],
        mode="markers",
        marker={"size": 16, "color": "red"},
    )
    return m


@reactive.effect
def update_map() -> None:
    m = lmap.value
    if m is None:
        return
    m.set_center(lat=37.6, lon=-122.4, zoom=input.zoom())
    m.update_traces(marker_color=input.color(), selector={"mode": "markers"})
