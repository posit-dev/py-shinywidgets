import plotly.express as px
from shiny.express import ui
from shinywidgets import render_plotly

df = px.data.iris()

ui.page_opts(title="Iris in 3D", fillable=True)


@render_plotly
def plot3d():
    return px.scatter_3d(
        df,
        x="sepal_length",
        y="sepal_width",
        z="petal_width",
        color="species",
        size="petal_length",
        size_max=18,
    )
