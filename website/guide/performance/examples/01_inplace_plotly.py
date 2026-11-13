import numpy as np
import pandas as pd
import plotly.express as px
from shiny import reactive
from shiny.express import input, ui
from shinywidgets import render_plotly

ui.page_opts(title="plotly: re-render vs in-place", fillable=True)

N = 5000
rng = np.random.default_rng(42)
df = pd.DataFrame({"x": rng.normal(size=N), "y": rng.normal(size=N)})

ui.input_action_button("inplace", "Update in place (batch_update)")
ui.input_action_button("rerender", "Force re-render (new figure)")

color_toggle = reactive.value(False)
rerender_trigger = reactive.value(0)


@render_plotly
def plot():
    # Reads rerender_trigger so clicking "rerender" forces a fresh figure;
    # the in-place path never touches this and so never re-enters here.
    rerender_trigger()
    with reactive.isolate():
        is_red = color_toggle()
    color = "red" if is_red else "blue"
    fig = px.scatter(df, x="x", y="y", color_discrete_sequence=[color])
    return fig.update_traces(marker=dict(size=4))


@reactive.effect
@reactive.event(input.inplace)
def _inplace():
    with reactive.isolate():
        is_red = not color_toggle()
    color_toggle.set(is_red)
    with plot.widget.batch_update():
        for trace in plot.widget.data:
            trace.marker.color = "red" if is_red else "blue"


@reactive.effect
@reactive.event(input.rerender)
def _rerender():
    with reactive.isolate():
        color_toggle.set(not color_toggle())
    rerender_trigger.set(rerender_trigger() + 1)
