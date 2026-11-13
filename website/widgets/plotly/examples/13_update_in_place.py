import plotly.express as px
from shiny import reactive
from shiny.express import input, ui
from shinywidgets import render_plotly

df = px.data.gapminder().query("year == 2007").reset_index(drop=True)

ui.page_opts(title="Resize markers without rebuilding the plot", fillable=True)

ui.input_slider("marker_size", "Marker size", min=4, max=24, value=8)


@render_plotly
def plot():
    # The render function never reads marker_size, so this never re-runs:
    # zoom and selection survive every slider move.
    return px.scatter(df, x="gdpPercap", y="lifeExp", color="continent", log_x=True)


@reactive.effect
def _resize():
    with plot.widget.batch_update():
        for trace in plot.widget.data:
            trace.marker.size = input.marker_size()
