from __future__ import annotations

# nglview creates a widget when it's imported, which shinywidgets only allows
# inside a session. Importing nglview before shinywidgets avoids that.
import nglview
from shiny import App, reactive, render, ui
from shinywidgets import output_widget, reactive_read, render_nglview

TINY_PDB = """\
HETATM    1  O   HOH A   1       0.000   0.000   0.000  1.00  0.00           O
END
"""

app_ui = ui.page_fluid(
    ui.input_action_button("rerender", "Rerender"),
    ui.output_text("render_count"),
    ui.div(
        output_widget("view"),
        id="fill_container",
        style="height: 400px; border: 1px solid #ccc;",
        class_="d-flex flex-column html-fill-container",
    ),
    output_widget("fixed", height="250px"),
    ui.output_text("picked_atom"),
)


def server(input, output, session):
    counter = reactive.value(0)

    @reactive.effect
    @reactive.event(input.rerender)
    def _():
        counter.set(counter.get() + 1)

    @render.text
    def render_count():
        return str(counter.get())

    @render_nglview
    def view():
        counter.get()
        return nglview.show_text(TINY_PDB, ext="pdb")

    @render_nglview
    def fixed():
        return nglview.show_text(TINY_PDB, ext="pdb")

    @render.text
    def picked_atom():
        picked = reactive_read(view.widget, "picked")
        return picked["atom1"]["name"] if picked else "none"


app = App(app_ui, server)
