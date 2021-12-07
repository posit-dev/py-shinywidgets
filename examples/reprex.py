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
        # TODO: jquery-ui slider bug?
        ipy.IntRangeSlider(
            value=[5, 7],
            min=0,
            max=10,
            step=1,
            description='Test:',
            disabled=False,
            continuous_update=False,
            orientation='horizontal',
            readout=True,
            readout_format='d',
        )
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
