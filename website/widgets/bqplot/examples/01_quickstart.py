# bqplot quick start: a scatter plot colored by species
import bqplot
import plotly.express as px
from shiny.express import ui
from shinywidgets import render_bqplot

ui.page_opts(title="bqplot quick start", fillable=True)

iris = px.data.iris()

with ui.card(full_screen=True):

    @render_bqplot
    def plot():
        x_sc, y_sc = bqplot.LinearScale(), bqplot.LinearScale()
        c_sc = bqplot.OrdinalColorScale(scheme="Set1")
        scatter = bqplot.Scatter(
            x=iris["sepal_length"],
            y=iris["petal_length"],
            color=iris["species"],
            scales={"x": x_sc, "y": y_sc, "color": c_sc},
            default_size=28,
            stroke="white",
        )
        return bqplot.Figure(
            marks=[scatter],
            axes=[
                bqplot.Axis(scale=x_sc, label="Sepal length (cm)"),
                bqplot.Axis(
                    scale=y_sc, orientation="vertical", label="Petal length (cm)"
                ),
            ],
            title="Iris",
        )
