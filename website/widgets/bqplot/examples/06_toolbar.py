# The figure's built-in toolbar (pan/zoom, reset, save as PNG) needs its own
# widgets in the browser. shinywidgets opens their Python counterparts on
# demand, so the buttons work without any extra code.
import bqplot
import plotly.express as px
from shiny.express import ui
from shinywidgets import render_bqplot

ui.page_opts(title="Toolbar", fillable=True)

iris = px.data.iris()

with ui.card(full_screen=True):
    ui.card_header("Hover the plot to reveal the toolbar")

    @render_bqplot
    def plot():
        x_sc, y_sc = bqplot.LinearScale(), bqplot.LinearScale()
        scatter = bqplot.Scatter(
            x=iris["sepal_length"],
            y=iris["petal_length"],
            scales={"x": x_sc, "y": y_sc},
            colors=["#4c78a8"],
        )
        return bqplot.Figure(
            marks=[scatter],
            axes=[bqplot.Axis(scale=x_sc), bqplot.Axis(scale=y_sc, orientation="vertical")],
            display_toolbar=True,
        )
