# nglview creates a widget when it's imported, which shinywidgets only allows
# inside a session. Importing nglview before shinywidgets avoids that.
import nglview
from shiny import App, render, ui
from shinywidgets import output_widget, reactive_read, render_nglview

REPRESENTATIONS = ["cartoon", "licorice", "spacefill", "surface"]

app_ui = ui.page_fillable(
    ui.layout_sidebar(
        ui.sidebar(
            ui.input_select("representation", "Representation", REPRESENTATIONS),
            ui.input_select(
                "color_scheme",
                "Color scheme",
                ["residueindex", "element", "chainindex", "bfactor"],
            ),
            ui.hr(),
            ui.p("Click an atom to select it:"),
            ui.output_text("picked_atom"),
        ),
        ui.card(
            ui.card_header("Structure 1U19 (rhodopsin), filling its card"),
            output_widget("structure"),
            full_screen=True,
        ),
    ),
    title="nglview",
)


def server(input, output, session):
    @render_nglview
    def structure():
        view = nglview.show_file(nglview.datafiles.PDB, default_representation=False)
        view.add_representation(
            input.representation(), color_scheme=input.color_scheme()
        )
        view.center()
        return view

    @render.text
    def picked_atom():
        picked = reactive_read(structure.widget, "picked")
        return picked["atom1"]["name"] if picked else "Nothing selected yet"


app = App(app_ui, server)
