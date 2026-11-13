# Choropleth explorer -- a small, adaptable starting point for a leafmap dashboard.
# template | ~65 lines
# Run: uv run --with geopandas,mapclassify shiny run docs/widget-guides/leafmap/gallery/template_choropleth_explorer.py
# Data: Natural Earth countries (via leafmap's example data on GitHub)
import geopandas as gpd
import leafmap
from shiny.express import input, render, ui
from shinywidgets import render_leafmap

COUNTRIES_URL = "https://raw.githubusercontent.com/opengeos/leafmap/master/examples/data/countries.geojson"
COUNTRIES = gpd.read_file(COUNTRIES_URL)
COLUMNS = {
    "GDP_MD_EST": "GDP (million USD)",
    "POP_EST": "Population",
    "POP_RANK": "Population rank",
}

ui.page_opts(title="Choropleth explorer", fillable=True)

with ui.sidebar():
    ui.input_select("column", "Shade by", COLUMNS, selected="GDP_MD_EST")
    ui.input_select(
        "scheme", "Classification", ["Quantiles", "EqualInterval", "NaturalBreaks"]
    )
    ui.input_slider("k", "Classes", min=3, max=9, value=6)
    ui.markdown("Hover a country on the map for its value; pan or zoom to explore.")

with ui.layout_columns(col_widths=(8, 4)):

    @render_leafmap
    def map():
        m = leafmap.Map(center=(20, 0), zoom=2)
        m.add_data(
            COUNTRIES,
            column=input.column(),
            scheme=input.scheme(),
            k=input.k(),
            cmap="YlOrRd",
            legend_title=COLUMNS[input.column()],
            layer_name="choropleth",
            info_mode="on_hover",
        )
        return m

    with ui.card():
        ui.card_header("Top 5")

        @render.data_frame
        def top5():
            # Swap COUNTRIES for your own data source (a database query, an
            # uploaded file, ...) -- the map and this table both key off
            # input.column(), so everything else here still works
            col = input.column()
            return COUNTRIES[["NAME", col]].nlargest(5, col).reset_index(drop=True)
