import pyvista as pv
from pyvista import examples
from shiny import reactive
from shiny.express import input, render, ui
from shinywidgets import render_pyvista

pv.OFF_SCREEN = True

ui.page_opts(fillable=True)
ui.input_select("field", "Color by", {"Elevation": "Elevation", "Curvature": "Mean curvature"})

CMAPS = {"Elevation": "terrain", "Curvature": "coolwarm"}


@reactive.calc
def hills():
    mesh = examples.load_random_hills()
    mesh["Curvature"] = mesh.curvature("mean")
    return mesh


with ui.layout_columns(col_widths=(8, 4)):
    with ui.card(full_screen=True):

        @render_pyvista
        def plot():
            pl = pv.Plotter()
            field = input.field()
            pl.add_mesh(hills(), scalars=field, cmap=CMAPS[field], show_scalar_bar=True)
            pl.view_isometric()
            return pl

    with ui.card():
        ui.card_header("Active field summary")

        @render.code
        def stats():
            values = hills()[input.field()]
            return f"min {values.min():.2f}\nmean {values.mean():.2f}\nmax {values.max():.2f}"
