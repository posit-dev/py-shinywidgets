# pydeck layers in a reactive Shiny map: 140,000 UK road accidents, binned on the GPU.
#
# pydeck >= 0.9 no longer ships an ipywidget, so @render_pydeck can't render a Deck.
# pydeck's layer API still works, though: a maplibre Map accepts pdk.Layer objects
# directly, and @render_maplibre turns the map into a two-way Shiny output.
import numpy as np
import pandas as pd
import pydeck as pdk
from maplibre import Map, MapOptions
from maplibre.basemaps import Carto
from shiny import reactive
from shiny.express import input, render, ui
from shinywidgets import reactive_read, render_maplibre

URL = "https://raw.githubusercontent.com/visgl/deck.gl-data/master/examples/3d-heatmap/heatmap-data.csv"
df = pd.read_csv(URL).dropna().round(4)
LNG, LAT = df["lng"].to_numpy(), df["lat"].to_numpy()
# [lng, lat] pairs + the "-" accessor (the row itself) serialize to ~half the JSON
# of a DataFrame with get_position=["lng", "lat"]. Every set_deck_layers() resends it.
POINTS = df[["lng", "lat"]].to_numpy().tolist()
PROBE_KM = 5
TOOLTIP = {"hex": "{{ elevationValue }} accidents"}
COLORS = [
    [1, 152, 189],
    [73, 227, 206],
    [216, 254, 181],
    [254, 237, 177],
    [254, 173, 84],
    [209, 55, 78],
]

ui.page_opts(title="140,000 UK road accidents, binned on the GPU", fillable=True)

with ui.layout_sidebar():
    with ui.sidebar(width=280):
        ui.input_slider("radius", "Hexagon radius (m)", 1000, 10000, 4000, step=500)
        ui.input_slider("elevation", "Elevation scale", 0, 200, 80)
        ui.input_slider("coverage", "Coverage", 0.3, 1, 0.85, step=0.05)
        ui.markdown(
            "Sliders restyle the map **in place** (the camera stays put).\n\n"
            "**Pan/zoom** to count what's on screen, **click** to probe a "
            f"{PROBE_KM} km radius, **right-drag** to tilt."
        )

    with ui.layout_columns(fill=False):
        with ui.value_box(
            showcase=ui.HTML("&#128269;"), theme="bg-gradient-blue-indigo"
        ):
            "Accidents in view"

            @render.text
            def in_view():
                n = int(visible().sum())
                return f"{n:,} ({n / len(df):.0%})"

        with ui.value_box(
            showcase=ui.HTML("&#128205;"), theme="bg-gradient-orange-red"
        ):
            f"Within {PROBE_KM} km of your click"

            @render.text
            def near_click():
                c = clicked()
                return (
                    f"{int(within_km(c, PROBE_KM).sum()):,}" if c else "Click the map"
                )

    with ui.card(full_screen=True):

        @render_maplibre
        def deck():
            m = Map(
                MapOptions(
                    style=Carto.DARK_MATTER,
                    center=(-1.9, 52.25),
                    zoom=6,
                    pitch=50,
                    bearing=-18,
                    max_pitch=70,
                )
            )
            # An empty overlay: the effect below fills it (calls made before the map
            # renders are queued), so the points cross the wire once, not twice.
            m.add_deck_layers([], tooltip=TOOLTIP)
            return m

        @reactive.effect
        def _restyle():
            deck.widget.set_deck_layers(layers(clicked()), tooltip=TOOLTIP)


def layers(click: dict | None) -> list[pdk.Layer]:
    hexes = pdk.Layer(
        "HexagonLayer",
        POINTS,
        id="hex",
        get_position="-",
        radius=input.radius(),
        elevation_scale=input.elevation(),
        elevation_range=[0, 3000],
        extruded=True,
        coverage=input.coverage(),
        color_range=COLORS,
        pickable=True,
        auto_highlight=True,
        material=True,
    )
    if not click:
        return [hexes]
    probe = pdk.Layer(
        "ScatterplotLayer",
        [[click["lng"], click["lat"]]],
        id="probe",
        get_position="-",
        get_radius=PROBE_KM * 1000,
        filled=True,
        get_fill_color=[255, 255, 255, 60],
        stroked=True,
        get_line_color=[255, 230, 0],
        line_width_min_pixels=3,
        parameters={"depthCompare": "always"},  # draw on top of the extruded hexagons
    )
    return [hexes, probe]


@reactive.calc
def clicked() -> dict | None:
    return reactive_read(deck.widget, "clicked") or None


@reactive.calc
def visible() -> np.ndarray:
    vs = reactive_read(deck.widget, "view_state")
    if not vs:
        return np.ones(len(df), dtype=bool)
    sw, ne = vs["bounds"]["_sw"], vs["bounds"]["_ne"]
    return (
        (LNG >= sw["lng"])
        & (LNG <= ne["lng"])
        & (LAT >= sw["lat"])
        & (LAT <= ne["lat"])
    )


def within_km(click: dict, km: float) -> np.ndarray:
    dx = (LNG - click["lng"]) * 111.32 * np.cos(np.radians(click["lat"]))
    dy = (LAT - click["lat"]) * 110.57
    return dx**2 + dy**2 <= km**2
