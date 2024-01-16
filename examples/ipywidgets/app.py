import shiny.express
from ipywidgets import IntSlider
from shiny import render

from shinywidgets import reactive_read, render_widget


@render_widget
def slider():
    return IntSlider(
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

@render.ui
def slider_val():
    val = reactive_read(slider.widget, "value")
    return f"The value of the slider is: {val}"
