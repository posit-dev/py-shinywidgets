import mapwidget.leaflet
import mapwidget.maplibre
from shiny import App, reactive, render, ui
from shinywidgets import output_widget, reactive_read, render_mapwidget

backends = {
    "maplibre": "MapLibre GL (vector tiles, WebGL)",
    "leaflet": "Leaflet (raster tiles)",
}

app_ui = ui.page_fillable(
    ui.layout_sidebar(
        ui.sidebar(
            ui.input_select("backend", "Backend", backends),
            ui.output_text_verbatim("state"),
            ui.p(
                "Pan or zoom the map, or click it, and the state below updates. ",
                "The same app code drives either backend -- only the Map class differs.",
                class_="text-muted small",
            ),
        ),
        ui.card(
            ui.card_header("mapwidget"),
            output_widget("map"),
            full_screen=True,
        ),
        title="render_mapwidget",
    )
)


def server(input, output, session):
    @render_mapwidget
    def map():
        if input.backend() == "leaflet":
            return mapwidget.leaflet.Map(center=[40, -100], zoom=4)
        return mapwidget.maplibre.Map(center=[40, -100], zoom=4)

    @render.text
    def state():
        center = reactive_read(map.widget, "center")
        zoom = reactive_read(map.widget, "zoom")
        clicked = reactive_read(map.widget, "clicked_latlng")
        return f"center: {center}\nzoom: {zoom}\nclicked: {clicked}"


app = App(app_ui, server)
