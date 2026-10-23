import nglview
from shiny import App, ui
from shinywidgets import output_widget, render_widget

PDB = """ATOM      1  N   ALA A   1      11.104   6.134  -6.504  1.00  0.00           N
ATOM      2  CA  ALA A   1      11.639   6.071  -5.147  1.00  0.00           C
ATOM      3  C   ALA A   1      10.612   5.462  -4.202  1.00  0.00           C
ATOM      4  O   ALA A   1       9.469   5.220  -4.592  1.00  0.00           O
ATOM      5  CB  ALA A   1      12.918   5.246  -5.063  1.00  0.00           C
END
"""
app_ui = ui.page_fillable(
    ui.card(output_widget("v"), style="height:500px"),
)
def server(input, output, session):
    @render_widget
    def v():
        w = nglview.show_text(PDB, ext="pdb") if hasattr(nglview, "show_text") else None
        return w
app = App(app_ui, server)
