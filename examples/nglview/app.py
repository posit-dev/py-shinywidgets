import nglview
from nglview.color import ColormakerRegistry
from shiny import App, reactive, render, ui
from shinywidgets import output_widget, reactive_read, render_nglview

REPRESENTATIONS = ["cartoon", "licorice", "spacefill", "surface"]

# A custom color scheme, registered once on nglview's process-global
# ColormakerRegistry; every session's browser receives it
ColormakerRegistry.add_selection_scheme(
    "custom", [["red", "hetero"], ["lightblue", "*"]]
)

COLOR_SCHEMES = ["residueindex", "element", "chainindex", "bfactor", "custom"]

app_ui = ui.page_fillable(
    ui.layout_sidebar(
        ui.sidebar(
            ui.input_select("representation", "Representation", REPRESENTATIONS),
            ui.input_select("color_scheme", "Color scheme", COLOR_SCHEMES),
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
        view.add_representation("cartoon", color_scheme="residueindex")
        view.center()
        return view

    # Update the displayed viewer in place (no re-render) when the inputs change
    @reactive.effect
    def _():
        view = structure.widget
        if view is None:
            return
        view.clear_representations()
        view.add_representation(
            input.representation(), color_scheme=input.color_scheme()
        )

    @render.text
    def picked_atom():
        picked = reactive_read(structure.widget, "picked")
        # A pick on a surface representation has no atom, so `picked` can be
        # nonempty without an "atom1" entry (e.g. only "bond"/"instanceId")
        atom = picked.get("atom1") if picked else None
        return atom["name"] if atom else "Nothing selected yet"


app = App(app_ui, server)
