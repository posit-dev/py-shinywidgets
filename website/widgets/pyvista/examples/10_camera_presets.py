import pyvista as pv
from pyvista import examples
from shiny import reactive
from shiny.express import input, ui
from shinywidgets import render_pyvista

pv.OFF_SCREEN = True

ui.page_opts(fillable=True)
with ui.layout_columns(col_widths=12, fill=False):
    ui.input_action_button("iso", "Isometric")
    ui.input_action_button("top", "Top")
    ui.input_action_button("front", "Front")

view = reactive.value("iso")


@reactive.effect
@reactive.event(input.iso)
def _():
    view.set("iso")


@reactive.effect
@reactive.event(input.top)
def _():
    view.set("top")


@reactive.effect
@reactive.event(input.front)
def _():
    view.set("front")


@render_pyvista
def plot():
    pl = pv.Plotter()
    pl.add_mesh(examples.load_random_hills(), scalars="Elevation", cmap="terrain")
    {"iso": pl.view_isometric, "top": pl.view_xy, "front": pl.view_xz}[view()]()
    return pl
