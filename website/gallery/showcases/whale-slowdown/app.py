# Title: Ships slow down for whales
# Bucket: showcase
# Description: 2.68M AIS vessel pings on a lonboard GPU map, crossfiltered by
#   four Mosaic selections (region, speed, vessel type, hour). Brushing a
#   region flies the map to it and lists the cargo/tankers that did NOT slow
#   down -- revealing the 10-knot voluntary speed limit that protects whales
#   in the Santa Barbara Channel.
# Run: shiny run app.py
# Data: NOAA Marine Cadastre AIS, 2023-06-01 (33 MB parquet, downloaded on
#   first run; rebuild from the raw CSV with prep_data.py).

import math
import shutil
import time
import urllib.request
from collections.abc import Callable
from pathlib import Path
from typing import Any, TypeVar

import duckdb
import geopandas as gpd
import numpy as np
import pandas as pd
from lonboard import Map, ScatterplotLayer
from lonboard._map import MapViewState
from lonboard.basemap import CartoStyle, MaplibreBasemap
from mosaic_widget import MosaicWidget
from shiny import App, reactive, render, req, ui
from shinywidgets import output_widget, reactive_read, render_lonboard, render_mosaic_widget

from ships import MAX_HIGHLIGHT, highlight_sample, slowpokes

DATA_URL = "https://github.com/cpsievert/py-shinywidgets-data/releases/download/showcase-v1/pings.parquet"
DATA = Path(__file__).parent / "data" / "pings.parquet"

if not DATA.exists():
    DATA.parent.mkdir(exist_ok=True)
    print(f"Downloading {DATA.name} (~33 MB, one time) ...", flush=True)
    tmp = DATA.with_suffix(".part")
    with urllib.request.urlopen(DATA_URL) as resp, open(tmp, "wb") as f:
        shutil.copyfileobj(resp, f, length=1 << 20)
    tmp.rename(DATA)
SELECTIONS = ["region", "speed", "kind", "hour"]
DEBOUNCE_S = 0.3

PALETTE: dict[str, tuple[int, int, int]] = {
    "cargo": (66, 146, 255),
    "tanker": (255, 112, 67),
    "passenger": (102, 214, 120),
    "fishing": (250, 204, 21),
    "tug": (186, 134, 255),
    "pleasure": (64, 214, 214),
    "other": (140, 140, 150),
}
HIGHLIGHT_RGB = [255, 255, 255]
US_VIEW = {"longitude": -96.0, "latitude": 36.5, "zoom": 3.2}
MAP_WIDTH_PX = 870

CON = duckdb.connect()
CON.execute(f"CREATE TABLE pings AS SELECT * FROM read_parquet('{DATA}')")
BASE = CON.sql("SELECT lon, lat, vessel_group FROM pings").df()
BASE_GDF = gpd.GeoDataFrame(geometry=gpd.points_from_xy(BASE.lon, BASE.lat), crs="EPSG:4326")
BASE_COLORS = np.array([PALETTE[g] for g in BASE.vessel_group], dtype=np.uint8)
N_PINGS = len(BASE)
N_VESSELS = int(CON.sql("SELECT count(DISTINCT mmsi) AS n FROM pings").df()["n"].iloc[0])
NO_PINGS = pd.DataFrame({"lon": [], "lat": [], "sog": []})

T = TypeVar("T")


def histogram(col: str, label: str, domain: list[float], step: float, width: int, height: int) -> dict[str, Any]:
    return {
        "plot": [
            {"mark": "rectY", "data": {"from": "pings", "filterBy": f"$not_{col_sel(col)}"},
             "x": {"bin": col, "step": step}, "y": {"count": ""}, "fill": "#7cc4ff", "inset": 0.5, "clip": True},
            {"select": "intervalX", "as": f"${col_sel(col)}"},
        ],
        "xDomain": domain, "xLabel": label, "yLabel": None, "yTicks": 3, "yTickFormat": "s",
        "width": width, "height": height, "marginLeft": 45,
    }  # fmt: skip


def col_sel(col: str) -> str:
    return {"sog": "speed", "hour": "hour"}[col]


SPEC: dict[str, Any] = {
    "params": {
        **{name: {"select": "intersect"} for name in SELECTIONS},
        **{
            f"not_{name}": {"select": "intersect", "include": [f"${o}" for o in SELECTIONS if o != name]}
            for name in SELECTIONS
        },
    },
    "vconcat": [
        {
            "plot": [
                {"mark": "raster", "data": {"from": "pings", "filterBy": "$not_region"},
                 "x": "lon", "y": "lat", "fill": "density", "pixelSize": 2},
                {"select": "intervalXY", "as": "$region"},
            ],
            "xDomain": [-127, -65], "yDomain": [23, 50], "colorScale": "symlog", "colorScheme": "magma",
            "xLabel": "Longitude", "yLabel": "Latitude", "width": 560, "height": 250, "marginLeft": 45,
        },
        histogram("sog", "Speed over ground (knots) →", [0, 25], 0.5, 560, 130),
        {
            "hconcat": [
                {
                    "plot": [
                        {"mark": "barX", "data": {"from": "pings", "filterBy": "$not_kind"},
                         "x": {"count": ""}, "y": "vessel_group", "fill": "#7cc4ff", "sort": {"y": "-x"}},
                        {"select": "toggleY", "as": "$kind"},
                        {"select": "highlight", "by": "$kind"},
                    ],
                    "xAxis": None, "yLabel": None,
                    "width": 240, "height": 140, "marginLeft": 70,
                },
                histogram("hour", "Hour (UTC) →", [0, 24], 1, 320, 140),
            ]
        },
    ],
}  # fmt: skip

app_ui = ui.page_fillable(
    ui.input_dark_mode(mode="dark", style="display: none"),
    ui.tags.style(
        """
        .showcase-title { display: flex; align-items: baseline; gap: 1rem; margin-bottom: .25rem; }
        .showcase-title h1 { font-size: 1.4rem; margin: 0; }
        .showcase-title p { margin: 0; color: var(--bs-secondary-color); }
        #caption { font-size: 1.05rem; }
        .mosaic-card .card-body { overflow: auto; }
        """
    ),
    ui.div(
        ui.h1("Ships slow down for whales"),
        ui.p(f"{N_PINGS:,} moving AIS pings from {N_VESSELS:,} vessels in US waters on 1 June 2023"),
        class_="showcase-title",
    ),
    ui.layout_columns(
        ui.card(output_widget("map"), class_="p-0"),
        ui.layout_columns(
            ui.card(
                ui.card_header(ui.output_ui("caption")),
                output_widget("dash", height="530px", fill=False),
                class_="mosaic-card",
                fill=False,
            ),
            ui.card(
                ui.card_header("Didn't slow down: cargo and tankers with a median of 12+ knots in the brushed region"),
                ui.output_ui("slowpoke_table"),
            ),
            col_widths=12,
            row_heights=["auto", "1fr"],
        ),
        col_widths=[7, 5],
    ),
    title="Ships slow down for whales",
    padding="1rem",
)


def server(input: Any, output: Any, session: Any) -> None:
    @render_lonboard
    def map():
        base = ScatterplotLayer.from_geopandas(
            BASE_GDF, get_fill_color=BASE_COLORS, radius_units="pixels", get_radius=1, opacity=0.35
        )
        return Map(
            [base, highlight_layer(NO_PINGS)],
            basemap=MaplibreBasemap(style=CartoStyle.DarkMatter),
            view_state=MapViewState(**US_VIEW),
        )

    @render_mosaic_widget
    def dash():
        return MosaicWidget(SPEC, con=CON.cursor())

    @debounce(DEBOUNCE_S)
    def params() -> dict[str, Any]:
        w = dash.widget
        req(w is not None)
        assert w is not None
        p: dict[str, Any] = reactive_read(w, "params")
        req(set(SELECTIONS) <= set(p))
        return p

    def active(p: dict[str, Any], names: list[str]) -> bool:
        return any(p[n].get("predicate", "").strip() for n in names)

    @reactive.calc
    def selected() -> duckdb.DuckDBPyRelation:
        params()
        w = dash.widget
        assert w is not None
        return w.data("pings", filter_by=SELECTIONS)

    @reactive.calc
    def n_selected() -> int:
        row = selected().aggregate("count(*)").fetchone()
        return int(row[0]) if row else 0

    @render.ui
    def caption():
        p = params()
        if not active(p, SELECTIONS):
            return ui.span("Brush any chart. Mosaic crossfilters in DuckDB; the map highlights the selection.")
        n = n_selected()
        shown = min(n, MAX_HIGHLIGHT)
        note = f" (map shows a {shown:,} sample)" if n > MAX_HIGHLIGHT else ""
        return ui.span(ui.strong(f"{n:,}"), f" pings selected{note}", id="selected-count", data_n=str(n))

    @reactive.effect
    def _update_highlight():
        p = params()
        w = map.widget
        if w is None:
            return
        sel = highlight_sample(selected()) if active(p, SELECTIONS) else NO_PINGS
        with reactive.isolate():
            base = w.layers[0]
            base.opacity = 0.12 if len(sel) else 0.35
            w.layers = [base, highlight_layer(sel)]

    region_bounds: reactive.Value[tuple[float, float, float, float] | None] = reactive.value(None)

    @reactive.effect
    def _track_region():
        region_bounds.set(brush_bounds(params()["region"]))

    @reactive.effect
    @reactive.event(region_bounds, ignore_init=True, ignore_none=False)
    def _fly_to_region():
        bounds = region_bounds()
        w = map.widget
        if w is None:
            return
        view = US_VIEW if bounds is None else fit_view(*bounds)
        w.fly_to(**view, duration=1500)

    @render.ui
    def slowpoke_table():
        p = params()
        if not p["region"].get("predicate", "").strip():
            return ui.p("Brush a region on the density map to list vessels that kept up speed there.",
                        class_="text-secondary mb-0")  # fmt: skip
        w = dash.widget
        assert w is not None
        rel = w.data("pings", filter_by=["region", "kind"]).filter("vessel_group IN ('cargo', 'tanker')")
        df = slowpokes(rel)
        if df.empty:
            return ui.p("Every cargo ship and tanker here slowed down.", class_="text-secondary mb-0")
        df = df.assign(median_sog=df.median_sog.map("{:.1f} kn".format))
        df.columns = ["Vessel", "Type", "Pings", "Median speed"]
        return ui.HTML(df.to_html(index=False, classes="table table-sm mb-0", border=0))


def brush_bounds(param: dict[str, Any]) -> tuple[float, float, float, float] | None:
    value = param.get("value")
    if not param.get("predicate", "").strip() or not isinstance(value, list) or len(value) != 2:
        return None
    (x0, x1), (y0, y1) = value
    return min(x0, x1), max(x0, x1), min(y0, y1), max(y0, y1)


def fit_view(lon0: float, lon1: float, lat0: float, lat1: float) -> dict[str, float]:
    span = max(lon1 - lon0, (lat1 - lat0) * 1.3, 0.05)
    zoom = math.log2(MAP_WIDTH_PX * 360 / (512 * span))
    return {"longitude": (lon0 + lon1) / 2, "latitude": (lat0 + lat1) / 2, "zoom": min(zoom, 12)}


def highlight_layer(df: pd.DataFrame) -> ScatterplotLayer:
    # lonboard can't build a layer from zero geometries
    pts = df if len(df) else pd.DataFrame({"lon": [0.0], "lat": [0.0]})
    gdf = gpd.GeoDataFrame(geometry=gpd.points_from_xy(pts.lon, pts.lat), crs="EPSG:4326")
    return ScatterplotLayer.from_geopandas(
        gdf,
        get_fill_color=HIGHLIGHT_RGB,
        radius_units="pixels",
        get_radius=1.6,
        opacity=0.9,
        visible=bool(len(df)),
    )


def debounce(delay_s: float) -> Callable[[Callable[[], T]], Callable[[], T]]:
    def wrapper(fn: Callable[[], T]) -> Callable[[], T]:
        deadline: reactive.Value[float | None] = reactive.value(None)
        trigger = reactive.value(0)

        @reactive.calc
        def latest() -> T:
            return fn()

        @reactive.effect(priority=102)
        def _prime():
            try:
                latest()
            finally:
                deadline.set(time.monotonic() + delay_s)

        @reactive.effect(priority=101)
        def _timer():
            due = deadline()
            if due is None:
                return
            left = due - time.monotonic()
            if left > 0:
                reactive.invalidate_later(left)
                return
            with reactive.isolate():
                deadline.set(None)
                trigger.set(trigger() + 1)

        @reactive.calc
        @reactive.event(trigger)
        def settled() -> T:
            return latest()

        return settled

    return wrapper


app = App(app_ui, server)
