import geopandas as gpd
import numpy as np
import pandas as pd
from lonboard import ScatterplotLayer
from shiny import App, reactive, render, ui
from shinywidgets import output_widget, reactive_read, render_lonboard

rng = np.random.default_rng(0)

# Synthetic "sightings" scattered around a handful of US cities
CITIES = {
    "Seattle": (-122.33, 47.61),
    "San Francisco": (-122.42, 37.77),
    "Denver": (-104.99, 39.74),
    "Chicago": (-87.63, 41.88),
    "Atlanta": (-84.39, 33.75),
    "New York": (-74.01, 40.71),
}
COLORS = {
    city: color
    for city, color in zip(
        CITIES,
        [
            [31, 119, 180],
            [255, 127, 14],
            [44, 160, 44],
            [214, 39, 40],
            [148, 103, 189],
            [140, 86, 75],
        ],
    )
}


def sightings(n: int) -> gpd.GeoDataFrame:
    city = rng.choice(list(CITIES), n)
    lon, lat = np.array([CITIES[c] for c in city]).T
    df = pd.DataFrame(
        {
            "city": city,
            "lon": lon + rng.normal(0, 2.5, n),
            "lat": lat + rng.normal(0, 1.5, n),
        }
    )
    return gpd.GeoDataFrame(
        df, geometry=gpd.points_from_xy(df.lon, df.lat), crs="EPSG:4326"
    )


app_ui = ui.page_sidebar(
    ui.sidebar(
        ui.input_select(
            "n",
            "Number of points",
            {"10000": "10,000", "100000": "100,000", "500000": "500,000"},
            selected="100000",
        ),
        ui.input_slider("radius", "Point radius (pixels)", 1, 10, 2),
        ui.input_switch("by_city", "Color by city", True),
        ui.p(
            "Changing the radius or colors restyles the layer in place: the points "
            "aren't sent to the browser again.",
            class_="text-muted small",
        ),
        ui.hr(),
        ui.h6("View state"),
        ui.output_text_verbatim("view_state"),
        ui.h6("Clicked point"),
        ui.output_text_verbatim("clicked"),
        width=320,
    ),
    ui.card(
        ui.card_header("Sightings"),
        output_widget("map"),
        full_screen=True,
    ),
    title="lonboard + Shiny",
    fillable=True,
)


def server(input, output, session):
    @reactive.calc
    def data() -> gpd.GeoDataFrame:
        return sightings(int(input.n()))

    def fill_color():
        if not input.by_city():
            return [0, 0, 0, 255]
        return np.array([COLORS[c] for c in data()["city"]], dtype=np.uint8)

    @render_lonboard
    def map():
        # Only re-render when the data changes; styling is updated in place below
        with reactive.isolate():
            style = {
                "radius_min_pixels": input.radius(),
                "get_fill_color": fill_color(),
            }
        return ScatterplotLayer.from_geopandas(
            data(), pickable=True, auto_highlight=True, **style
        )

    def layer():
        m = map.widget
        assert m is not None
        return m.layers[0]

    @reactive.effect
    @reactive.event(input.radius, ignore_init=True)
    def _():
        layer().radius_min_pixels = input.radius()

    @reactive.effect
    @reactive.event(input.by_city, ignore_init=True)
    def _():
        layer().get_fill_color = fill_color()

    @render.text
    def view_state():
        state = reactive_read(map.widget, "view_state")
        if state is None:
            return "(not yet known)"
        return (
            f"longitude: {state.longitude:.3f}\n"
            f"latitude: {state.latitude:.3f}\n"
            f"zoom: {state.zoom:.2f}"
        )

    @render.text
    def clicked():
        index = reactive_read(layer(), "selected_index")
        if index is None:
            return "Click a point on the map"
        row = data().iloc[index]
        return f"#{index}: near {row.city}\n({row.lon:.3f}, {row.lat:.3f})"


app = App(app_ui, server)
