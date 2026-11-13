import plotly.express as px
from shiny.express import ui
from shinywidgets import render_plotly

df = px.data.iris()

ui.page_opts(title="Iris", fillable=True)


@render_plotly
def plot():
    return px.scatter(
        df, x="sepal_width", y="sepal_length", color="species", title="Iris"
    )
