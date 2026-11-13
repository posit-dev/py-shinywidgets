import math

import geopandas as gpd
import plotly.express as px
from lonboard import ScatterplotLayer
from shapely.geometry import box
from shiny import req
from shiny.express import input, ui
from shinywidgets import render_lonboard, render_plotly

ui.page_opts(fillable=True)

CITIES_URL = "https://raw.githubusercontent.com/nvkelso/natural-earth-vector/master/geojson/ne_110m_populated_places.geojson"

# lonboard's view_state has no bounds field (only center + zoom), so compute
# the viewport's lng/lat box from Web Mercator math, using the output's
# on-screen pixel size (reported once and on every resize).
ui.head_content(
    ui.tags.script("""
    $(document).on("shiny:connected", function() {
      function send() {
        var el = document.querySelector("#map");
        if (el) Shiny.setInputValue("map_px", [el.clientWidth, el.clientHeight]);
      }
      new ResizeObserver(send).observe(document.body);
      setTimeout(send, 300);
    });
    """)
)

with ui.layout_columns(col_widths=[7, 5]):
    with ui.card(full_screen=True):

        @render_lonboard
        def map():
            cities = gpd.read_file(CITIES_URL)
            return ScatterplotLayer.from_geopandas(
                cities, get_fill_color=[255, 60, 120], radius_min_pixels=4
            )

    with ui.card():
        ui.card_header("Largest cities currently in view")

        @render_plotly
        def chart():
            vs = map.view_state()
            width, height = req(input.map_px())
            bounds = view_bounds(vs.longitude, vs.latitude, vs.zoom, width, height)
            cities = gpd.read_file(CITIES_URL)
            visible = cities[cities.geometry.within(box(*bounds))]
            top = visible.nlargest(12, "POP_MAX").sort_values("POP_MAX")
            fig = px.bar(top, x="POP_MAX", y="NAME", orientation="h")
            fig.update_layout(
                title=f"{len(visible)} cities in view", margin=dict(l=10, r=10, t=40, b=10)
            )
            return fig


def inv_merc(y: float) -> float:
    return math.degrees(2 * math.atan(math.exp(y)) - math.pi / 2)


def view_bounds(
    lon: float, lat: float, zoom: float, width: float, height: float
) -> tuple[float, float, float, float]:
    """(minx, miny, maxx, maxy) of a Web Mercator viewport (512px tiles)."""
    world_px = 512 * 2**zoom
    half_w = (width / 2) * 360 / world_px
    half_h = (height / 2) * (2 * math.pi) / world_px
    m = math.log(math.tan(math.pi / 4 + math.radians(lat) / 2))
    return (lon - half_w, inv_merc(m - half_h), lon + half_w, inv_merc(m + half_h))
