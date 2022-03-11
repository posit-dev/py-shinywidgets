from ipyshiny import *
from htmltools import *
from shiny import *
import ipywidgets as ipy


app_ui = ui.page_fluid(
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
    ui.output_ui("value")
)

def server(input, output, session):
    @output(name="value")
    @render_ui()
    def _():
        return input.widget()

app = App(app_ui, server)
