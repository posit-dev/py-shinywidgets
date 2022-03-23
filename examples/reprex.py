from ipyshiny import *
from htmltools import *
from shiny import *
import ipywidgets as ipy


app_ui = ui.page_fluid(
    output_ipywidget("value")
)

def server(input, output, session):
    d = ipy.DatePicker(
        description='Pick a Date',
        disabled=False
    )

    @output(name="value")
    @render_ipywidget()
    def _():
        return d

app = App(app_ui, server)
