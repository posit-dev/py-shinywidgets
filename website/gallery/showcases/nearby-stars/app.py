# Title: Every star within 330 light-years
# Bucket: showcase
# Description: 256k Gaia DR3 stars linked across three widget libraries: lasso
#   the jscatter HR diagram and the same stars highlight in a k3d 3D view and
#   an ipyaladin sky view. Preset buttons (white dwarfs, Hyades, halo
#   visitors) drive all three widgets from Python.
# Run: shiny run app.py
# Data: ESA Gaia DR3 (16 MB parquet, downloaded on first run; rebuild from
#   the Gaia archive with prep_data.py). The sky panel streams DSS imagery
#   (CDS's DSS2 color survey, served from NASA/IRSA's mirror), so it needs
#   network access.

import shutil
import time
import urllib.request
from collections.abc import Callable
from pathlib import Path
from typing import Any, TypeVar

import jscatter
import k3d
import numpy as np
import numpy.typing as npt
import pandas as pd
from ipyaladin import Aladin
from k3d.plot import Plot
from matplotlib import colormaps
from matplotlib.colors import LinearSegmentedColormap
from shiny import App, reactive, render, req, ui
from shinywidgets import output_widget, reactive_read, render_ipyaladin, render_jscatter, render_k3d

from stars import MAX_SKY_MARKERS, fast_mask, hyades_mask, sky_table, white_dwarf_mask

DATA_URL = "https://github.com/cpsievert/py-shinywidgets-data/releases/download/showcase-v1/stars.parquet"
DATA = Path(__file__).parent / "data" / "stars.parquet"

if not DATA.exists():
    DATA.parent.mkdir(exist_ok=True)
    print(f"Downloading {DATA.name} (~16 MB, one time) ...", flush=True)
    tmp = DATA.with_suffix(".part")
    with urllib.request.urlopen(DATA_URL) as resp, open(tmp, "wb") as f:
        shutil.copyfileobj(resp, f, length=1 << 20)
    tmp.rename(DATA)
DEBOUNCE_S = 0.3
SURVEY = "https://irsa.ipac.caltech.edu/data/hips/CDS/DSS2/color"
SKY_ALL = {"target": "66.75 15.87", "fov": 360.0}
HYADES_SKY = {"target": "66.75 15.87", "fov": 20.0}

STARS = pd.read_parquet(DATA).assign(neg_abs_g=lambda d: -d["abs_g"])
XYZ = STARS[["x", "y", "z"]].to_numpy(np.float32)

PRESETS: dict[str, tuple[npt.NDArray[np.intp], str]] = {
    "white_dwarfs": (
        np.flatnonzero(white_dwarf_mask(STARS)),
        "white dwarfs: the burnt-out cores of Sun-like stars. Small, faint, and all around us.",
    ),
    "hyades": (
        np.flatnonzero(hyades_mask(STARS)),
        "stars picked by motion alone, ~47 pc away, trace one thin sequence: the Hyades cluster, born together.",
    ),
    "halo": (
        np.flatnonzero(fast_mask(STARS)),
        "stars faster than 150 km/s sit below the main sequence: old, metal-poor halo stars just passing through.",
    ),
}
# Light at both ends so every star reads on a dark background
SPEED_CMAP = LinearSegmentedColormap.from_list("speed", ["#6f8fc0", "#a9d6f5", "#ffd166", "#ff4d6d"])
DIST_CMAP = LinearSegmentedColormap.from_list("dist", ["#ffe8a3", "#7fd1b9", "#5a8fd8"])
COLOR_BY: dict[str, tuple[str, LinearSegmentedColormap, tuple[float, float]]] = {
    "vtan": ("Tangential speed (km/s)", SPEED_CMAP, (0.0, 150.0)),
    "dist_pc": ("Distance (pc)", DIST_CMAP, (0.0, 100.0)),
}
HR_X = (-0.6, 5.0)
HR_Y = (-19.0, 3.0)
HR_CAMERA_DISTANCE = 1.25

T = TypeVar("T")


def rgb_uint32(values: npt.NDArray[np.floating[Any]], cmap: str, lo: float, hi: float) -> npt.NDArray[np.uint32]:
    rgba = colormaps[cmap](np.clip((values - lo) / (hi - lo), 0, 1))
    rgb = (rgba[:, :3] * 255).astype(np.uint32)
    return (rgb[:, 0] << 16) | (rgb[:, 1] << 8) | rgb[:, 2]


BASE_COLORS = rgb_uint32(STARS["bp_rp"].to_numpy(), "RdYlBu_r", 0.0, 3.0)
HYADES_CENTER = XYZ[PRESETS["hyades"][0]].mean(axis=0)
HOME_CAMERA = [0.0, -230.0, 110.0, 0.0, 0.0, 0.0, 0.0, 0.0, 1.0]

app_ui = ui.page_sidebar(
    ui.sidebar(
        ui.h5("Presets (selected from Python)"),
        ui.input_action_button("white_dwarfs", "White dwarfs", class_="btn-outline-light"),
        ui.input_action_button("hyades", "Hyades", class_="btn-outline-light"),
        ui.input_action_button("halo", "Halo visitors", class_="btn-outline-light"),
        ui.input_action_button("reset", "Clear selection", class_="btn-outline-secondary"),
        ui.hr(),
        ui.input_radio_buttons(
            "color_by", "Color the HR diagram by", {k: v[0] for k, v in COLOR_BY.items()}, selected="vtan"
        ),
        ui.hr(),
        ui.output_ui("caption"),
        ui.p(
            "Lasso stars on the HR diagram (drag). Esc clears. Scroll to zoom.",
            class_="text-secondary small mt-auto mb-0",
        ),
        width=290,
    ),
    ui.input_dark_mode(mode="dark", style="display: none"),
    ui.layout_columns(
        ui.card(ui.card_header("Hertzsprung-Russell diagram: colour vs. luminosity"), output_widget("hr")),
        ui.layout_columns(
            ui.card(ui.card_header("Where they are: 3D, Sun at the centre (pc)"), output_widget("space")),
            ui.card(ui.card_header("Where they are on the sky"), output_widget("sky")),
            col_widths=12,
            row_heights=[1, 1],
        ),
        col_widths=[7, 5],
    ),
    title=f"Every star within 330 light-years: {len(STARS):,} stars from Gaia DR3",
    fillable=True,
)


def server(input: Any, output: Any, session: Any) -> None:
    active_preset: reactive.Value[str | None] = reactive.value(None)
    pushed = reactive.value((0, 0))

    @render_jscatter
    def hr():
        _, cmap, norm = COLOR_BY["vtan"]
        return (
            jscatter.Scatter(data=STARS, x="bp_rp", y="neg_abs_g", x_scale=HR_X, y_scale=HR_Y)
            .color(by="vtan", map=cmap, norm=norm)
            .size(default=2)
            .axes(axes=True, grid=False, labels=["BP-RP colour (hot/blue to cool/red)", "−Absolute G mag (brighter ↑)"])
            .legend(True)
            .mouse(mode="lasso")
            .camera(distance=HR_CAMERA_DISTANCE)
            .background("#1d1f21")
        )

    @render_k3d
    def space():
        plot = Plot(
            grid_visible=False,
            menu_visibility=False,
            background_color=0x1D1F21,
            axes_helper=0,
            camera_auto_fit=False,
        )
        plot.camera = HOME_CAMERA
        plot += k3d.points(XYZ, colors=BASE_COLORS, point_size=0.6, shader="flat", opacity=0.35)
        plot += k3d.points(np.zeros((1, 3), np.float32), color=0xFFFFFF, point_size=1.6, shader="flat", visible=False)
        plot += k3d.points(np.zeros((1, 3), np.float32), color=0xFFD700, point_size=5, shader="3d")
        return plot

    @render_ipyaladin
    def sky():
        # The all-sky fov is applied after the switch to AIT (SIN clamps it), so start smaller
        return Aladin(survey=SURVEY, target=SKY_ALL["target"], fov=60, show_coo_grid_control=False)

    @reactive.effect
    def _all_sky_projection():
        w = sky.widget
        if w is not None and reactive_read(w, "_is_loaded"):
            with reactive.isolate():
                w.projection = "AIT"
                w.fov = SKY_ALL["fov"]

    @debounce(DEBOUNCE_S)
    def selection() -> npt.NDArray[np.intp]:
        w = hr.widget
        req(w is not None)
        sel = reactive_read(w, "selection")
        return np.asarray(sel if sel is not None else [], dtype=np.intp)

    @reactive.effect
    def _forget_preset_on_manual_selection():
        sel = selection()
        with reactive.isolate():
            name = active_preset()
        if name is not None and not np.array_equal(np.sort(sel), PRESETS[name][0]):
            active_preset.set(None)

    def apply_preset(name: str) -> None:
        ids = PRESETS[name][0]
        active_preset.set(name)
        scatter = hr.value
        scatter.selection(ids)
        scatter.zoom(to=ids, animation=800, padding=0.3)
        space_w = space.widget
        if space_w is not None:
            if name == "hyades":
                cx, cy, cz = (float(v) for v in HYADES_CENTER)
                space_w.camera = [cx + 25, cy + 25, cz + 18, cx, cy, cz, 0, 0, 1]
            else:
                space_w.camera = HOME_CAMERA
        sky_w = sky.widget
        if sky_w is not None:
            view = HYADES_SKY if name == "hyades" else SKY_ALL
            sky_w.target = view["target"]
            sky_w.fov = view["fov"]

    @reactive.effect
    @reactive.event(input.white_dwarfs)
    def _():
        apply_preset("white_dwarfs")

    @reactive.effect
    @reactive.event(input.hyades)
    def _():
        apply_preset("hyades")

    @reactive.effect
    @reactive.event(input.halo)
    def _():
        apply_preset("halo")

    @reactive.effect
    @reactive.event(input.reset)
    def _():
        active_preset.set(None)
        hr.value.selection([])
        hr.value.camera(target=(0.0, 0.0), distance=HR_CAMERA_DISTANCE)
        space_w = space.widget
        if space_w is not None:
            space_w.camera = HOME_CAMERA
        sky_w = sky.widget
        if sky_w is not None:
            sky_w.target = SKY_ALL["target"]
            sky_w.fov = SKY_ALL["fov"]

    @reactive.effect
    @reactive.event(input.color_by, ignore_init=True)
    def _recolor():
        _, cmap, norm = COLOR_BY[input.color_by()]
        hr.value.color(by=input.color_by(), map=cmap, norm=norm)

    @reactive.effect
    def _update_space():
        sel = selection()
        w = space.widget
        if w is None:
            return
        highlight = w.objects[1]
        if len(sel):
            highlight.positions = XYZ[sel]
            highlight.visible = True
        else:
            highlight.visible = False
        with reactive.isolate():
            pushed.set((len(sel), pushed()[1]))

    @reactive.effect
    def _update_sky():
        sel = selection()
        w = sky.widget
        if w is None or not reactive_read(w, "_is_loaded"):
            return
        try:
            w.remove_overlay("selection")
        except ValueError:
            pass
        table = sky_table(STARS.iloc[sel]) if len(sel) else None
        if table is not None:
            w.add_table(table, name="selection", color="#ffd700", shape="circle", source_size=10)
        with reactive.isolate():
            pushed.set((pushed()[0], 0 if table is None else len(table)))

    @render.ui
    def caption():
        sel = selection()
        n3d, nsky = pushed()
        if not len(sel):
            return ui.p(
                "Lasso a region of the HR diagram, or pick a preset.",
                id="selection-caption", data_n="0", data_space=str(n3d), data_sky=str(nsky), class_="mb-0",
            )  # fmt: skip
        name = active_preset()
        text = PRESETS[name][1] if name is not None else "stars selected."
        sky_note = f"Sky shows the {nsky:,} brightest." if len(sel) > MAX_SKY_MARKERS else ""
        return ui.div(
            ui.p(ui.strong(f"{len(sel):,}"), " ", text, class_="mb-1"),
            ui.p(sky_note, class_="text-secondary small mb-0"),
            id="selection-caption",
            data_n=str(len(sel)),
            data_preset=name or "",
            data_space=str(n3d),
            data_sky=str(nsky),
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
