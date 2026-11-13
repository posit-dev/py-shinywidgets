# Title: Terrain explorer
# A real DEM you can orbit, click to read elevation at the cursor, fly to the
# high/low points, and toggle wireframe -- all without rebuilding the scene.
# Bucket: showcase
# Run: shiny run app.py
# Data: the Jacksboro Fault DEM shipped inside matplotlib's sample data
# (344x403 elevation grid, Texas; downsampled 2x here for responsiveness).
from __future__ import annotations

import k3d
import matplotlib.cbook as cbook
import numpy as np
from shiny import reactive
from shiny.express import input, render, ui
from shinywidgets import render_k3d

elevation = cbook.get_sample_data("jacksboro_fault_dem.npz")["elevation"][::2, ::2].astype(np.float32)
nrows, ncols = elevation.shape
BOUNDS = (-10.0, 10.0, -10.0, 10.0)
relief = (elevation - elevation.min()) / (elevation.max() - elevation.min()) * 4.0

peak_row, peak_col = np.unravel_index(np.argmax(elevation), elevation.shape)
valley_row, valley_col = np.unravel_index(np.argmin(elevation), elevation.shape)
HOME = [16, -18, 14, 0, 0, 1, 0, 0, 1]


def grid_xyz(row: int, col: int) -> tuple[float, float, float]:
    xmin, xmax, ymin, ymax = BOUNDS
    x = xmin + col / (ncols - 1) * (xmax - xmin)
    y = ymin + row / (nrows - 1) * (ymax - ymin)
    return x, y, float(relief[row, col])


def nearest_grid_cell(x: float, y: float) -> tuple[int, int]:
    xmin, xmax, ymin, ymax = BOUNDS
    col = round((x - xmin) / (xmax - xmin) * (ncols - 1))
    row = round((y - ymin) / (ymax - ymin) * (nrows - 1))
    return int(np.clip(row, 0, nrows - 1)), int(np.clip(col, 0, ncols - 1))


clicked = reactive.value(None)

ui.page_opts(title="Jacksboro Fault terrain", fillable=True)
with ui.layout_columns():
    ui.input_action_button("home", "Home")
    ui.input_action_button("peak", "Fly to highest point")
    ui.input_action_button("valley", "Fly to lowest point")
    ui.input_checkbox("wireframe", "Wireframe", value=False)

with ui.layout_columns(col_widths=[8, 4]):
    with ui.card(full_screen=True):
        ui.card_header("Drag to orbit, click to inspect elevation")

        @render_k3d
        def terrain():
            plot = k3d.plot(mode="callback", camera_auto_fit=False)
            plot.camera = HOME
            plot += k3d.surface(
                relief,
                bounds=BOUNDS,
                attribute=elevation,
                color_map=k3d.matplotlib_color_maps.Terrain,
                color_range=[float(elevation.min()), float(elevation.max())],
                click_callback=lambda info: clicked.set(info),
                name="dem",
            )
            # A marker for the clicked / flown-to point, hidden until used
            plot += k3d.points([[0, 0, 0]], point_size=0.3, color=0xE45756, visible=False, name="marker")
            return plot

    with ui.card(full_screen=True):
        ui.card_header("Picked point")

        @render.code
        def picked():
            info = clicked()
            if info is None:
                return "None (click the terrain)"
            x, y, _ = info["position"]
            row, col = nearest_grid_cell(x, y)
            return f"elevation: {elevation[row, col]:.0f} m\nrow, col: {row}, {col}"

        ui.card_header("Camera")

        @render.code
        def camera_out():
            cam = terrain.camera()
            return "\n".join(f"{v:.1f}" for v in cam[:3])


@reactive.effect
def _toggle_wireframe():
    terrain.widget.objects[0].wireframe = input.wireframe()


def fly_to(x: float, y: float, z: float) -> None:
    marker = terrain.widget.objects[1]
    marker.positions = np.array([[x, y, z]], dtype=np.float32)
    marker.visible = True
    terrain.widget.camera = [x + 6, y - 6, z + 5, x, y, z, 0, 0, 1]


@reactive.effect
@reactive.event(input.home)
def _home():
    terrain.widget.objects[1].visible = False
    terrain.widget.camera = HOME


@reactive.effect
@reactive.event(input.peak)
def _fly_peak():
    fly_to(*grid_xyz(peak_row, peak_col))


@reactive.effect
@reactive.event(input.valley)
def _fly_valley():
    fly_to(*grid_xyz(valley_row, valley_col))


@reactive.effect
def _mark_clicked():
    info = clicked()
    if info is None:
        return
    x, y, z = info["position"]
    marker = terrain.widget.objects[1]
    marker.positions = np.array([[x, y, z]], dtype=np.float32)
    marker.visible = True
