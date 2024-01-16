import altair as alt
import shiny.express
from shiny import render
from vega_datasets import data

from shinywidgets import reactive_read, render_altair


# Output selection information (click on legend in the plot)
@render.text
def selection():
    pt = reactive_read(jchart.widget.selections, "point")
    return "Selected point: " + str(pt)

# Replicate JupyterChart interactivity
# https://altair-viz.github.io/user_guide/jupyter_chart.html#point-selections
@render_altair
def jchart():
    brush = alt.selection_point(name="point", encodings=["color"], bind="legend")
    return alt.Chart(data.cars()).mark_point().encode(
        x='Horsepower:Q',
        y='Miles_per_Gallon:Q',
        color=alt.condition(brush, 'Origin:N', alt.value('grey')),
    ).add_params(brush)
