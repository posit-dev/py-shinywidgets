from shiny import *
from ipyshiny import *
import ipywidgets as ipy


app_ui = ui.page_fluid(
    output_ipywidget("slider"),
    ui.output_text("value")
)

def server(input, output, session):
    s = ipy.IntSlider(
        value=7,
        min=0,
        max=10,
        step=1,
        description='Test:',
        disabled=False,
        continuous_update=False,
        orientation='horizontal',
        readout=True,
        readout_format='d'
    )
    
    # This should print on every client-side change to the slider
    s.observe(lambda change: print(change.new), "value")

    @output(name="slider")
    @render_ipywidget()
    def _():
        return s



app = App(app_ui, server)
