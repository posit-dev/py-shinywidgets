import plotly.express as px
from shiny.express import ui
from shinywidgets import render_plotly

df = px.data.iris()

ui.page_opts(title="Sizing", fillable=True)

with ui.card(full_screen=True):
    "Fills its card (no explicit height) -- try full_screen"

    @render_plotly
    def fills():
        return px.scatter(df, x="sepal_width", y="sepal_length", color="species")


with ui.card():
    "Fixed height: an explicit height= sizes the plot directly"

    @render_plotly(height="300px")
    def fixed():
        return px.scatter(df, x="sepal_width", y="sepal_length", color="species")
