import leafmap
from shiny.express import ui
from shinywidgets import render_leafmap

COUNTRIES = "https://raw.githubusercontent.com/opengeos/leafmap/master/examples/data/countries.geojson"

ui.page_opts(title="leafmap vector data", fillable=True)


@render_leafmap
def map():
    m = leafmap.Map(center=(20, 0), zoom=2)
    m.add_basemap("CartoDB.Positron")
    # add_geojson/add_gdf take a style dict, a per-feature style_callback, and a
    # hover tooltip built from every property -- no manual GeoJSON layer wiring
    m.add_geojson(
        COUNTRIES,
        layer_name="Countries",
        style_callback=lambda feat: {
            "fillColor": "#2a9d8f"
            if feat["properties"]["CONTINENT"] == "Africa"
            else "#264653",
            "color": "white",
            "weight": 0.5,
            "fillOpacity": 0.6,
        },
        hover_style={"fillOpacity": 0.9, "weight": 2},
        info_mode="on_hover",
    )
    return m
