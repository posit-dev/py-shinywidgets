from ipyshiny import *
from htmltools import *
from shiny import *
import ipywidgets as ipy
import os
import sys

shiny_module_dir = os.path.dirname(os.path.dirname(__file__))
sys.path.insert(0, shiny_module_dir)


ui = page_fluid(
    input_ipywidget(
        "widget",
        ipy.Button(
            description='Click me',
            disabled=False,
            button_style='',  # 'success', 'info', 'warning', 'danger' or ''
            tooltip='Click me',
            icon='check'
        ),
    ),
    output_ui("value")
)

def server(ss: ShinySession):
    @ss.output("value")
    @render_ui()
    def _():
        return ss.input["widget"]

app = ShinyApp(ui, server)
if __name__ == "__main__":
    app.run()
