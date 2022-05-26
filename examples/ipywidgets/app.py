from shiny import *
from ipyshiny import *
import ipywidgets as ipy
from ipywidgets.widgets.widget import Widget


app_ui = ui.page_fluid(output_widget("slider"), ui.output_text("value"))


def server(input: Inputs, output: Outputs, session: Session):
    s: Widget = ipy.IntSlider(
        value=7,
        min=0,
        max=10,
        step=1,
        description="Test:",
        disabled=False,
        continuous_update=False,
        orientation="horizontal",
        readout=True,
        readout_format="d",
    )

    # This should print on every client-side change to the slider
    s.observe(lambda change: print(change.new), "value")

    @output()
    @render_widget()
    def slider():
        return s


app = App(app_ui, server)
