from ipyleaflet import GeoJSON, Map, WidgetControl
from ipywidgets import HTML
from shiny import App, ui
from shinywidgets import output_widget, render_widget

GEOJSON_DATA = {
    "type": "FeatureCollection",
    "features": [
        {
            "type": "Feature",
            "properties": {"name": "TestRegion"},
            "geometry": {
                "type": "Polygon",
                "coordinates": [
                    [
                        [-10, 40],
                        [10, 40],
                        [10, 60],
                        [-10, 60],
                        [-10, 40],
                    ]
                ],
            },
        }
    ],
}


app_ui = ui.page_fillable(
    output_widget("map"),
)


def server(input, output, session):
    @render_widget
    def map():
        m = Map(center=(50, 0), zoom=3)

        html = HTML("Hover over a region")
        html.layout.margin = "0px 20px 20px 20px"
        control = WidgetControl(widget=html, position="topright")
        m.add(control)

        geo_json = GeoJSON(
            data=GEOJSON_DATA,
            style={"opacity": 1, "fillOpacity": 0.3, "weight": 1},
            hover_style={"fillOpacity": 0.7},
        )

        def update_html(feature, **kwargs):
            html.value = f"<b>{feature['properties']['name']}</b>"

        geo_json.on_hover(update_html)
        m.add(geo_json)

        return m


app = App(app_ui, server)
