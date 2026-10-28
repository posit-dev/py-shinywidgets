from __future__ import annotations

import ipywidgets
import nglview
from nglview.color import ColormakerRegistry
from shiny import App, reactive, render, ui
from shinywidgets import output_widget, reactive_read, render_nglview, render_widget

TINY_PDB = """\
HETATM    1  O   HOH A   1       0.000   0.000   0.000  1.00  0.00           O
END
"""

# Several bonded atoms, so a licorice representation has something to draw
ALA_PDB = """\
ATOM      1  N   ALA A   1      11.104   6.134  -6.504  1.00  0.00           N
ATOM      2  CA  ALA A   1      11.639   6.071  -5.147  1.00  0.00           C
ATOM      3  C   ALA A   1      11.231   4.651  -5.304  1.00  0.00           C
ATOM      4  O   ALA A   1      12.076   3.808  -5.359  1.00  0.00           O
ATOM      5  CB  ALA A   1      13.144   6.284  -5.234  1.00  0.00           C
END
"""


class SubclassedNGLWidget(nglview.NGLWidget):
    """An app-defined subclass, whose widget_pkg() is this app's module."""


# The box the "Remove child" button empties (see boxed())
boxes: dict[str, ipywidgets.VBox] = {}

# A custom color scheme, registered once at import (process-global). Every
# session's browser needs it (the registry's view must render there)
ColormakerRegistry.add_selection_scheme("sw_blue", [["blue", "*"]])

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
    ui.input_action_button("add_spacefill", "Add spacefill in place"),
    output_widget("fixed", height="250px"),
    output_widget("own_height_view"),
    output_widget("width_view"),
    output_widget("sized_both", height="400px"),
    output_widget("layout_sized"),
    output_widget("custom_scheme"),
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

    @render_nglview
    def sized_both():
        # A constructor height (200px) must win over the output's 400px
        return nglview.NGLWidget(nglview.TextStructure(TINY_PDB), height="200px")

    @render_nglview
    def layout_sized():
        # An explicitly sized Layout must win over the output's size, and the
        # stage must follow once ipywidgets applies the styles to the view
        # root (it does so only after display). A constructor `layout=`
        # argument is not covered: nglview archives it raw into the synced
        # _ngl_msg_archive, which is not JSON serializable
        widget = nglview.NGLWidget(nglview.TextStructure(TINY_PDB))
        widget.layout = ipywidgets.Layout(width="200px", height="150px")
        return widget

    @render_nglview
    def custom_scheme():
        v = nglview.show_text(ALA_PDB, ext="pdb", default_representation=False)
        # The import-time scheme registration must reach this browser (and
        # every other session's) before this representation is created
        v.add_representation("licorice", color="sw_blue")
        return v

    @reactive.effect
    @reactive.event(input.add_spacefill)
    def _():
        v = view.widget
        if v is None:
            return
        # In-place mutation, sent from nglview's background thread: must reach
        # the browser without a re-render (render_count stays 0)
        v.add_representation("spacefill", color="sw_blue")

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
