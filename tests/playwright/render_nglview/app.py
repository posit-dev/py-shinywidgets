from __future__ import annotations

import ipywidgets
import nglview
from shiny import App, reactive, render, ui
from shinywidgets import output_widget, reactive_read, render_nglview, render_widget

TINY_PDB = """\
HETATM    1  O   HOH A   1       0.000   0.000   0.000  1.00  0.00           O
END
"""


class SubclassedNGLWidget(nglview.NGLWidget):
    """An app-defined subclass, whose widget_pkg() is this app's module."""


# The box the "Remove child" button empties (see boxed())
boxes: dict[str, ipywidgets.VBox] = {}

app_ui = ui.page_fluid(
    ui.input_action_button("rerender", "Rerender"),
    ui.input_action_button("own_height", "Rerender with own height"),
    ui.input_action_button("remove_child", "Remove child"),
    ui.output_text("render_count"),
    ui.div(
        output_widget("view"),
        id="fill_container",
        style="height: 400px; border: 1px solid #ccc;",
        class_="d-flex flex-column html-fill-container",
    ),
    ui.div(
        output_widget("subclassed"),
        id="subclass_container",
        style="height: 400px; border: 1px solid #ccc;",
        class_="d-flex flex-column html-fill-container",
    ),
    output_widget("fixed", height="250px"),
    output_widget("own_height_view"),
    output_widget("width_view"),
    output_widget("boxed"),
    ui.output_text("picked_atom"),
)


def server(input, output, session):
    counter = reactive.value(0)

    @reactive.effect
    @reactive.event(input.rerender)
    def _():
        counter.set(counter.get() + 1)

    @reactive.effect
    @reactive.event(input.remove_child)
    def _():
        # Dropping a child makes its container view call view.remove() on it
        boxes["box"].children = ()

    @render.text
    def render_count():
        return str(counter.get())

    @render_nglview
    def view():
        counter.get()
        widget = nglview.show_text(TINY_PDB, ext="pdb")
        # A widget-level height opts this render out of filling
        if input.own_height():
            widget.layout.height = "200px"
        return widget

    @render_nglview
    def subclassed():
        return SubclassedNGLWidget(nglview.TextStructure(TINY_PDB))

    @render_nglview
    def fixed():
        return nglview.show_text(TINY_PDB, ext="pdb")

    @render_nglview
    def own_height_view():
        widget = nglview.show_text(TINY_PDB, ext="pdb")
        widget.layout.height = "250px"
        return widget

    @render_nglview
    def width_view():
        # A constructor width opts out of tracking the output's width
        return nglview.NGLWidget(
            nglview.TextStructure(TINY_PDB), width="200px", height="200px"
        )

    @render_widget
    def boxed():
        box = ipywidgets.VBox([nglview.show_text(TINY_PDB, ext="pdb")])
        boxes["box"] = box
        return box

    @render.text
    def picked_atom():
        picked = reactive_read(view.widget, "picked")
        atom = picked.get("atom1") if picked else None
        return atom["name"] if atom else "none"


app = App(app_ui, server)
