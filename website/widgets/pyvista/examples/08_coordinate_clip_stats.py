import pyvista as pv
from pyvista import examples
from shiny import reactive
from shiny.express import input, render, ui
from shinywidgets import render_pyvista

pv.OFF_SCREEN = True

ui.page_opts(fillable=True)
ui.input_slider("cut", "Clip position (fraction of width)", 0.0, 1.0, 0.5, step=0.05)


@reactive.calc
def terrain():
    # Mount St. Helens, downloaded once per process and cached across re-renders
    dem = examples.download_st_helens()
    return dem.warp_by_scalar()


@reactive.calc
def visible_terrain():
    x0, x1, *_ = terrain().bounds
    cut_x = x0 + input.cut() * (x1 - x0)
    return terrain().clip(normal="x", origin=(cut_x, 0, 0))


with ui.layout_columns(col_widths=(8, 4)):
    with ui.card(full_screen=True):

        @render_pyvista
        def plot():
            pl = pv.Plotter()
            pl.add_mesh(
                visible_terrain(), scalars="Elevation", cmap="terrain", show_scalar_bar=False
            )
            pl.view_isometric()
            return pl

    with ui.card():
        ui.card_header("Stats for the visible slab")

        @render.code
        def stats():
            mesh = visible_terrain()
            elev = mesh["Elevation"]
            return (
                f"{mesh.n_points:,} points visible\n"
                f"mean elevation: {elev.mean():,.0f} m\n"
                f"max elevation: {elev.max():,.0f} m"
            )
