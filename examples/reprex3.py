from shiny import ui, reactive
import shiny as s
import ipyshiny
import ipysheet

app_ui = ui.page_fluid(
    ipyshiny.output_ipywidget("sheet"),
    ui.output_text("first_value")
)

def server(input: s.Inputs, output: s.Outputs, session: s.Session):
    x = reactive.Value()

    sheet1 = ipysheet.sheet()
    cell = ipysheet.cell(0, 0)
    cell.observe(lambda change: x.set(change["new"]), "value")

    @output(name="sheet")
    @ipyshiny.render_ipywidget()
    def _():
        return sheet1
    
    @output()
    def first_value():
        return x()


app = s.App(app_ui, server)