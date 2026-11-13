import geopandas as gpd
import matplotlib.pyplot as plt
from lonboard import PolygonLayer
from lonboard.colormap import apply_continuous_cmap
from shiny.express import ui
from shinywidgets import render_lonboard

ui.page_opts(fillable=True)

COUNTRIES_URL = "https://raw.githubusercontent.com/nvkelso/natural-earth-vector/master/geojson/ne_110m_admin_0_countries.geojson"


@render_lonboard
def map():
    countries = gpd.read_file(COUNTRIES_URL)
    countries = countries[countries.GDP_MD > 0].copy()
    gdp_per_capita = countries.GDP_MD * 1e6 / countries.POP_EST
    # apply_continuous_cmap() takes values in [0, 1] and any matplotlib
    # colormap (or a palettable Palette), returning one uint8 RGB row per value
    colors = apply_continuous_cmap(gdp_per_capita.rank(pct=True), plt.get_cmap("YlOrRd"))
    return PolygonLayer.from_geopandas(
        countries, get_fill_color=colors, get_line_color=[80, 80, 80], opacity=0.85
    )
