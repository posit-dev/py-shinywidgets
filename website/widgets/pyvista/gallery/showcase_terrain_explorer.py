# Mount St. Helens terrain explorer -- showcase bucket
# Ties three Shiny-input-driven re-render patterns to one dataset: a clip
# slider exposes a cross-section, a colormap/field selector recolors the
# surface, and a vertical-exaggeration slider restyles relief -- each
# paired with a Python-computed readout (and a matplotlib histogram) of
# the currently visible terrain, since nothing about the 3D view itself
# can be read back from the browser.
# Run: shiny run gallery/showcase_terrain_explorer.py
# Data: pyvista.examples.download_st_helens() (public-domain USGS DEM,
# downloaded once and cached locally by pyvista)

import matplotlib
import numpy as np
import pyvista as pv
from matplotlib.figure import Figure
from pyvista import examples
from shiny import reactive
from shiny.express import input, render, ui

from shinywidgets import render_pyvista

matplotlib.use("agg")
pv.OFF_SCREEN = True

ui.page_opts(fillable=True, title="Mount St. Helens terrain explorer")

with ui.sidebar():
    ui.input_slider("cut", "Clip position (fraction of width)", 0.0, 1.0, 1.0, step=0.05)
    ui.input_slider("exaggeration", "Vertical exaggeration", 1, 4, 2, step=0.5)
    ui.input_select(
        "field", "Color by", {"Elevation": "Elevation", "Slope": "Slope (degrees)"}
    )

CMAPS = {"Elevation": "terrain", "Slope": "magma"}


@reactive.calc
def dem():
    # Downloaded once per process; re-renders below only re-warp/re-clip it
    d = examples.download_st_helens()
    slope = d.compute_derivative(scalars="Elevation", gradient="gradient")
    gx, gy, _ = slope["gradient"].T
    d["Slope"] = np.degrees(np.arctan(np.hypot(gx, gy)))
    return d


@reactive.calc
def terrain():
    return dem().warp_by_scalar(factor=input.exaggeration())


@reactive.calc
def visible_terrain():
    x0, x1, *_ = terrain().bounds
    cut_x = x0 + input.cut() * (x1 - x0)
    if input.cut() >= 1.0:
        return terrain()
    return terrain().clip(normal="x", origin=(cut_x, 0, 0))


with ui.layout_columns(col_widths=(8, 4)):
    with ui.card(full_screen=True):
        ui.card_header("Mount St. Helens (USGS DEM, clipped and re-colored in Python)")

        @render_pyvista
        def plot():
            pl = pv.Plotter()
            field = input.field()
            pl.add_mesh(
                visible_terrain(), scalars=field, cmap=CMAPS[field], show_scalar_bar=True
            )
            pl.view_isometric()
            return pl

    with ui.card():
        ui.card_header("Visible terrain")

        @render.code
        def stats():
            mesh = visible_terrain()
            elev = mesh["Elevation"]
            return (
                f"{mesh.n_points:,} points visible\n"
                f"elevation: {elev.min():,.0f} - {elev.max():,.0f} m\n"
                f"mean: {elev.mean():,.0f} m"
            )

    with ui.card():
        ui.card_header("Elevation distribution (computed server-side)")

        @render.plot
        def histogram():
            fig = Figure(figsize=(4, 2.5), layout="constrained")
            ax = fig.subplots()
            ax.hist(visible_terrain()["Elevation"], bins=30, color="steelblue")
            ax.set_xlabel("Elevation (m)")
            ax.set_ylabel("Points")
            return fig
