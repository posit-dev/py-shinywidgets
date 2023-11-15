import ipywidgets as ipy
from ipywidgets.widgets.widget import Widget
from shiny import *

from shinywidgets import *

app_ui = ui.page_fluid(output_widget("slider", fillable=False, fill=False), ui.output_text("slider_val"))


def server(input: Inputs, output: Outputs, session: Session):

    @output
    @render_widget
    def slider():
        return ipy.IntSlider(
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

    @output
    @render.text
    def slider_val():
        val = reactive_read(slider.widget, "value")
        return f"The value of the slider is: {val}"


app = App(app_ui, server, debug=True)
