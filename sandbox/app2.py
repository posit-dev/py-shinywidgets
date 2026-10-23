import nglview
from shiny import App, ui
from shinywidgets import output_widget, render_widget

PDB = """ATOM      1  N   ALA A   1      11.104   6.134  -6.504  1.00  0.00           N
ATOM      2  CA  ALA A   1      11.639   6.071  -5.147  1.00  0.00           C
ATOM      3  C   ALA A   1      10.612   5.462  -4.202  1.00  0.00           C
END
"""
app_ui = ui.page_fluid(
    ui.div(output_widget("fill"), style="height:400px;display:flex;flex-direction:column;border:1px solid red", class_="html-fill-container", id="fillbox"),
    output_widget("explicit", height="250px"),
    output_widget("layouth"),
)
def server(input, output, session):
    @render_widget
    def fill():
        return nglview.show_text(PDB, ext="pdb")
    @render_widget
    def explicit():
        return nglview.show_text(PDB, ext="pdb")
    @render_widget
    def layouth():
        w = nglview.show_text(PDB, ext="pdb"); w.layout.height="220px"; return w
app = App(app_ui, server)
