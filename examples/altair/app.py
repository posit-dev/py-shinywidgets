import altair as alt
from shiny import App, render, ui
from vega_datasets import data

from shinywidgets import output_widget, reactive_read, register_widget

source = data.cars()

app_ui = ui.page_fluid(
    ui.output_text_verbatim("selection"),
    output_widget("chart")
)

def server(input, output, session):

    # Replicate JupyterChart interactivity
    # https://altair-viz.github.io/user_guide/jupyter_chart.html#point-selections
    brush = alt.selection_point(name="point", encodings=["color"], bind="legend")
    chart = alt.Chart(source).mark_point().encode(
        x='Horsepower:Q',
        y='Miles_per_Gallon:Q',
        color=alt.condition(brush, 'Origin:N', alt.value('grey')),
    ).add_params(brush)

    jchart = alt.JupyterChart(chart)

    # Display/register the chart in the app_ui
    register_widget("chart", jchart)

    # Reactive-ly read point selections
    @output
    @render.text
    def selection():
        pt = reactive_read(jchart.selections, "point")
        return "Selected point: " + str(pt)

app = App(app_ui, server)
