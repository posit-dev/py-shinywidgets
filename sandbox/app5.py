import nglview
from shiny import App, reactive, render, ui
from shinywidgets import output_widget, render_nglview
app_ui = ui.page_fillable(ui.input_action_button("go","go"), ui.input_action_button("bg","bg"), ui.output_text("n"), ui.card(output_widget("s")))
def server(input, output, session):
    @render_nglview
    def s():
        return nglview.show_file(nglview.datafiles.PDB)
    @reactive.effect
    @reactive.event(input.go)
    def _():
        v=s.widget; v.clear_representations(); v.add_representation("licorice"); print("called", v.loaded, flush=True)
    @reactive.effect
    @reactive.event(input.bg)
    def _():
        s.widget.background = "black"
    @render.text
    def n():
        return str(input.go()) + "/" + str(input.bg())
app = App(app_ui, server)
