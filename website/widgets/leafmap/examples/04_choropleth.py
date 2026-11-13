# Needs mapclassify for the classification scheme: `uv run --with mapclassify shiny run
# 04_choropleth.py` (or pip install mapclassify).
import leafmap
from shiny.express import ui
from shinywidgets import render_leafmap

COUNTRIES = "https://raw.githubusercontent.com/opengeos/leafmap/master/examples/data/countries.geojson"

ui.page_opts(title="leafmap choropleth", fillable=True)


@render_leafmap
def map():
    m = leafmap.Map(center=(20, 0), zoom=2)
    # add_data classifies a numeric column (here, Natural Earth's estimated GDP),
    # colors the layer, and adds the legend -- the one-liner version of a
    # geopandas .plot(column=...) choropleth
    m.add_data(
        COUNTRIES,
        column="GDP_MD_EST",
        scheme="Quantiles",
        k=6,
        cmap="YlGnBu",
        legend_title="GDP (million USD)",
        layer_name="GDP",
    )
    return m
