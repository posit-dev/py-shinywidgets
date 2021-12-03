# This will load the ipyshiny module dynamically, without having to install it.
# This makes the debug/run cycle quicker.
import os
import sys

shiny_module_dir = os.path.dirname(os.path.dirname(__file__))
sys.path.insert(0, shiny_module_dir)

import ipywidgets as ipy
from shiny import *
from ipyshiny import *

ui = page_fluid(
    input_ipywidget("IntSlider", ipy.IntSlider(value=4)),
    output_ui("value")
)

def server(ss: ShinySession):
    @ss.output("value")
    @render_ui()
    def _():
        return ss.input["IntSlider"]

app = ShinyApp(ui, server)
if __name__ == "__main__":
    app.run()
