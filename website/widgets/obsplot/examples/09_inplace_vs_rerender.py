from __future__ import annotations

import pandas as pd
from pyobsplot import Plot
from shiny import reactive
from shiny.express import input, render, ui

from shinywidgets import render_obsplot

ui.page_opts(title="In-place update vs. re-render", fillable=True)

data = pd.DataFrame({"x": range(30), "y": [((-1) ** i) * (i % 7) for i in range(30)]})


def spec(color: str = "black") -> dict:
    return {"marks": [Plot.line(data, {"x": "x", "y": "y", "stroke": color})]}


ui.input_action_button("rerender", "Rebuild the chart (re-render)")
ui.input_action_button("recolor", "Turn the line red (in place)")

render_count = reactive.value(0)


@render.code
def count():
    return f"full renders so far: {render_count.get()}"


with ui.card(full_screen=True):

    @render_obsplot
    def chart():
        input.rerender()
        with reactive.isolate():
            render_count.set(render_count.get() + 1)
        return Plot.plot(spec())


@reactive.effect
@reactive.event(input.recolor)
def _():
    # No re-render: pyobsplot redraws the same widget instance with the new
    # spec, so the ~1.4 MB anywidget JS bundle isn't resent and the output
    # never flashes its "recalculating" state.
    chart.widget.spec = spec("red")
