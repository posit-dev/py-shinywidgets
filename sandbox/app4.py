import nglview
from shiny import App, ui
from shinywidgets import output_widget, render_nglview
app_ui = ui.page_fillable(ui.card(ui.card_header("h"), output_widget("s"), full_screen=True))
def server(input, output, session):
    @render_nglview
    def s():
        return nglview.show_file(nglview.datafiles.PDB)
app = App(app_ui, server)
