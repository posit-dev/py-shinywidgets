import geopandas as gpd
import matplotlib.pyplot as plt
from lonboard import ScatterplotLayer
from lonboard.colormap import apply_continuous_cmap
from shiny import reactive
from shiny.express import input, ui
from shinywidgets import render_lonboard

ui.page_opts(fillable=True)

CITIES_URL = "https://raw.githubusercontent.com/nvkelso/natural-earth-vector/master/geojson/ne_110m_populated_places.geojson"

with ui.sidebar():
    ui.input_slider("radius", "Point radius (px)", 2, 20, 6)
    ui.input_switch("by_pop", "Color by population", False)
    ui.p(
        "Moving the slider or flipping the switch restyles the layer in "
        "place -- the 243 points cross the wire once, at first render.",
        class_="text-muted small",
    )

with ui.card(full_screen=True):

    @render_lonboard
    def map():
        # Read styling inputs under isolate(): this render function should
        # only re-run when the data changes, not on every slider tick
        with reactive.isolate():
            style = {"get_fill_color": fill_color(), "radius_min_pixels": input.radius()}
        return ScatterplotLayer.from_geopandas(cities(), **style)


@reactive.calc
def cities() -> gpd.GeoDataFrame:
    return gpd.read_file(CITIES_URL)


def fill_color():
    if not input.by_pop():
        return [255, 60, 120]
    pct = cities()["POP_MAX"].rank(pct=True).to_numpy()
    return apply_continuous_cmap(pct, plt.get_cmap("plasma"))


@reactive.effect
@reactive.event(input.radius, ignore_init=True)
def _update_radius():
    layer = map.widget.layers[0]
    layer.radius_min_pixels = input.radius()


@reactive.effect
@reactive.event(input.by_pop, ignore_init=True)
def _update_color():
    layer = map.widget.layers[0]
    layer.get_fill_color = fill_color()
