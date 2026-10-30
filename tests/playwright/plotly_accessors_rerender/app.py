import pandas as pd
import plotly.express as px
from shiny.express import input, render, ui
from shinywidgets import render_plotly

df = pd.DataFrame({"x": [1, 2, 3, 4, 5], "y": [1, 4, 9, 16, 25]})

ui.input_action_button("rerender", "rerender")


# The simplest app: one plot, one reader that runs in the same flush as the
# plot's first render (so before its comm opens)
@render_plotly
def plot():
    input.rerender()
    fig = px.scatter(df, x="x", y="y", custom_data=[df.index])
    fig.update_layout(dragmode="select")
    return fig


@render.text
def selected_rows():
    return ",".join(str(x) for x in plot.selected_rows(df)["x"])
