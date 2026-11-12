import pandas as pd
import plotly.express as px
from shiny import reactive
from shiny.express import render
from shinywidgets import render_plotly

df = pd.DataFrame({"x": [1, 2, 3, 4, 5], "y": [1, 4, 9, 16, 25]})

picked_x = reactive.Value(None)
render_count_value = reactive.Value(0)


@render_plotly
def plot():
    x = picked_x()
    with reactive.isolate():
        render_count_value.set(render_count_value() + 1)
    fig = px.scatter(df, x="x", y="y")
    fig.update_traces(marker_size=14)
    if x is not None:
        fig.add_vline(x=x, line_color="red")
    return fig


# The natural "click to mark" pattern: derive a value from the click and feed
# it back into the same output's render. The derived object is new on every
# derivation (reactive.Value dedupes only on identity), so this loops forever
# if a re-render re-runs readers of a kept accessor whose value didn't change
@reactive.effect
def _():
    pts = plot.clicked()
    if pts is None or len(pts) == 0:
        return
    picked_x.set(float(pts["x"].iloc[0]) * 1.0)


@render.text
def render_count():
    return str(render_count_value())
