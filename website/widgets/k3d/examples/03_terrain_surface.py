# Uses a real DEM (elevation grid) that ships inside matplotlib's sample data.
from __future__ import annotations

import k3d
import matplotlib.cbook as cbook
import numpy as np
from shiny.express import ui
from shinywidgets import render_k3d

elevation = cbook.get_sample_data("jacksboro_fault_dem.npz")["elevation"][::2, ::2].astype(np.float32)
relief = (elevation - elevation.min()) / (elevation.max() - elevation.min()) * 4.0

peak_row, peak_col = np.unravel_index(np.argmax(elevation), elevation.shape)
nrows, ncols = elevation.shape
peak_xyz = (
    -10 + peak_col / (ncols - 1) * 20,
    -10 + peak_row / (nrows - 1) * 20,
    float(relief[peak_row, peak_col]) + 0.3,
)

ui.page_opts(title="Jacksboro Fault DEM", fillable=True)


@render_k3d
def terrain():
    scene = k3d.plot(camera_auto_fit=False)
    scene.camera = [16, -18, 14, 0, 0, 1, 0, 0, 1]
    scene += k3d.surface(
        relief,
        bounds=[-10, 10, -10, 10],
        attribute=elevation,
        color_map=k3d.matplotlib_color_maps.Terrain,
        color_range=[float(elevation.min()), float(elevation.max())],
    )
    # is_html=True avoids k3d.text's default LaTeX rendering, which drops spaces
    # (e.g. "Highest point" renders as "Highestpoint")
    scene += k3d.text(
        "Highest point (1068 m)",
        position=peak_xyz,
        color=0x000000,
        label_box=True,
        is_html=True,
    )
    return scene
