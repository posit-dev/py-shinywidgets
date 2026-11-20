# Title: Which US counties are alike?
# Bucket: showcase (~240 lines)
# Description: K-means segmentation of 3,152 US counties on 8 socioeconomic
#   and health measures. Click a point on the silhouette chart to pick how
#   many segments to split the country into, and click a county on the map
#   to see its five closest matches nationwide, drawn as rings and lines
#   straight to their centroids.
# Run: shiny run app.py
# Data: County Health Rankings 2025 analytic file (University of Wisconsin
#   Population Health Institute), 260 KB parquet committed in data/; county
#   boundaries are plotly's public counties GeoJSON, cached under data/ on
#   first run.

import json
import shutil
import urllib.request
from pathlib import Path
from typing import Any

import figures
import pandas as pd
import segments
from segments import Clustering
from shiny import App, reactive, render, req, ui
from shinywidgets import output_widget, render_plotly

GEOJSON_URL = "https://raw.githubusercontent.com/plotly/datasets/master/geojson-counties-fips.json"
DATA = Path(__file__).parent / "data"
COUNTIES = pd.read_parquet(DATA / "counties.parquet")
FIPS_TO_POS = {fips: pos for pos, fips in enumerate(COUNTIES["fips"])}

GEOJSON_PATH = DATA / "geojson-counties-fips.json"
if not GEOJSON_PATH.exists():
    print("Downloading geojson-counties-fips.json (~3 MB, one time) ...", flush=True)
    tmp = GEOJSON_PATH.with_suffix(".part")
    with urllib.request.urlopen(GEOJSON_URL) as resp, open(tmp, "wb") as f:
        shutil.copyfileobj(resp, f, length=1 << 20)
    tmp.rename(GEOJSON_PATH)
with open(GEOJSON_PATH) as f:
    GEOJSON = json.load(f)
CENTROIDS = figures.build_centroids(GEOJSON)

KS = range(2, 11)
DEFAULT_K = 5
N_TWINS = 5
SILHOUETTE = segments.silhouette_by_k(COUNTIES, KS)
CLUSTERINGS: dict[int, Clustering] = {k: segments.fit(COUNTIES, k) for k in KS}


def muted(text: str, cls: str = "small") -> ui.Tag:
    return ui.p(text, style=f"color: {figures.TEXT_SECONDARY}", class_=cls)


def sub_header(main: str, sub: str) -> ui.CardItem:
    stack = ui.div(
        ui.div(main),
        ui.div(sub, style=f"color: {figures.TEXT_SECONDARY}", class_="small fw-normal"),
        style="display: flex; flex-direction: column; gap: .15rem",
    )  # fmt: skip
    return ui.card_header(stack)


app_ui = ui.page_sidebar(
    ui.sidebar(
        muted(
            f"{len(COUNTIES):,} US counties grouped by income, age, education, broadband, "
            "insurance, health, and rurality — never by race or ethnicity."
        ),
        ui.hr(class_="my-2"),
        ui.output_ui("k_summary"),
        ui.hr(class_="my-2"),
        ui.output_ui("selection_panel"),
        width=360,
        gap="0.5rem",
    ),
    ui.input_dark_mode(mode="dark", style="display: none"),
    ui.tags.style(f"""
        .twin {{ display: flex; align-items: center; gap: .4rem; padding: .15rem 0; font-size: .85rem; }}
        .twin .dot {{ width: .55rem; height: .55rem; border-radius: 50%; flex: none; }}
        .twin .name {{ font-weight: 500; flex: 1; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }}
        .twin .seg {{ font-size: .74rem; white-space: nowrap; color: {figures.TEXT_SECONDARY}; }}
        #selection_panel .twins-list {{ max-height: 30vh; overflow-y: auto; }}
        #map .choroplethlayer path, #silhouette .scatterlayer .points path {{ cursor: pointer; }}
    """),
    ui.layout_columns(
        ui.layout_columns(
            ui.card(
                ui.card_header("Click any county to see its five closest matches nationwide"),
                output_widget("map", fillable=True),
                full_screen=True,
            ),
            ui.card(
                sub_header("How many segments?", "Score peaks at k=2; more segments trade cohesion for detail."),
                output_widget("silhouette", fillable=True),
            ),
            col_widths=[8, 4],
        ),
        ui.card(
            sub_header("What each segment looks like", "Blue = below the US county average · Red = above average."),
            output_widget("heatmap", fillable=True),
            full_screen=True,
        ),
        col_widths=12,
        row_heights=[2, 1],
    ),
    title=f"Which US counties are alike? {len(COUNTIES):,} counties segmented by k-means",
    fillable=True,
)  # fmt: skip


def server(input: Any, output: Any, session: Any) -> None:
    k_value: reactive.Value[int] = reactive.value(DEFAULT_K)
    selected_fips: reactive.Value[str | None] = reactive.value(None)

    @reactive.calc
    def clustering() -> Clustering:
        return CLUSTERINGS[k_value()]

    @reactive.calc
    def twins() -> pd.DataFrame:
        fips = selected_fips()
        if fips is None:
            return COUNTIES.iloc[0:0]
        return segments.twins(COUNTIES, fips, N_TWINS)

    @render_plotly
    def map():
        return figures.build_map(CLUSTERINGS[DEFAULT_K], GEOJSON, COUNTIES)

    @render_plotly
    def silhouette():
        return figures.build_silhouette_chart(SILHOUETTE, DEFAULT_K)

    @render_plotly
    def heatmap():
        return figures.build_heatmap(CLUSTERINGS[DEFAULT_K])

    @reactive.effect
    def _update_map():
        w = map.widget
        if w is None:
            return
        with w.batch_update():
            figures.update_map(
                w, clustering(), selected_fips(), twins(), COUNTIES, CENTROIDS
            )

    @reactive.effect
    def _update_heatmap():
        w = heatmap.widget
        if w is None:
            return
        with w.batch_update():
            figures.update_heatmap(w, clustering())

    @reactive.effect
    def _restyle_silhouette():
        w = silhouette.widget
        if w is None:
            return
        with w.batch_update():
            figures.restyle_silhouette(w, SILHOUETTE, k_value())

    @reactive.effect
    def _pick_k_from_click():
        pts = silhouette.clicked()
        req(pts is not None)
        assert pts is not None
        k_value.set(int(round(pts["x"].iloc[0])))

    @reactive.effect
    def _select_county_from_click():
        pts = map.clicked()
        req(pts is not None)
        assert pts is not None
        pts = pts.loc[pts.loc[:, "trace_index"] == 0]
        req(len(pts) > 0)
        selected_fips.set(str(pts.loc[:, "customdata"].iloc[0]))

    @reactive.effect
    @reactive.event(input.clear_selection)
    def _clear_selection():
        selected_fips.set(None)

    @render.ui
    def k_summary():
        c = clustering()
        return ui.div(
            ui.h5(f"{c.k} segments", class_="mb-1"),
            muted(f"Silhouette {c.silhouette:.2f} · higher means more distinct segments.", "small mb-2"),
            ui.div(*[legend_item(i, c) for i in range(c.k)]),
        )  # fmt: skip

    @render.ui
    def selection_panel():
        fips = selected_fips()
        if fips is None:
            return muted(
                "Click a county on the map to see its five closest matches nationwide, "
                "by these 8 measures.",
                "small mb-0",
            )
        c = clustering()
        pos = FIPS_TO_POS[fips]
        row = COUNTIES.iloc[pos]
        seg = c.labels[pos]
        return ui.div(
            ui.h6(f"{row['county']}, {row['state']}", class_="mb-0"),
            muted(c.names[seg], "small mb-2"),
            ui.p("Closest matches nationwide:", class_="small fw-semibold mb-1"),
            ui.div(*[twin_item(r, c, seg) for r in twins().itertuples()], class_="twins-list"),
            muted(
                "Matches are nearest neighbors by these 8 measures — a close match can "
                "sit just across a segment boundary.",
                "small mt-2 mb-2",
            ),
            ui.input_action_link("clear_selection", "Clear selection", class_="small d-block"),
        )  # fmt: skip


def legend_item(i: int, c: Clustering) -> ui.Tag:
    return ui.div(
        ui.span(class_="dot", style=f"background-color: {figures.SEGMENT_COLORS[i]}"),
        ui.span(f"{i + 1}. {c.names[i]}", class_="small"),
        class_="twin",
    )


def twin_item(r: Any, c: Clustering, selected_seg: int) -> ui.Tag:
    seg = c.labels[FIPS_TO_POS[r.fips]]
    cells = [
        ui.span(class_="dot", style=f"background-color: {figures.SEGMENT_COLORS[seg]}"),
        ui.span(f"{r.county}, {r.state}", class_="name"),
    ]
    if seg != selected_seg:
        cells.append(ui.span(c.names[seg], class_="seg"))
    return ui.div(*cells, class_="twin")


app = App(app_ui, server)
