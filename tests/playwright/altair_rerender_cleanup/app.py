from __future__ import annotations

import altair as alt
import pandas as pd
from shiny import App, reactive, ui
from shinywidgets import output_widget, render_widget


app_ui = ui.page_fluid(
    ui.input_action_button("rerender", "Rerender"),
    output_widget("plot"),
)


def server(input, output, session):
    counter = reactive.value(0)

    @reactive.effect
    @reactive.event(input.rerender)
    def _():
        counter.set(counter.get() + 1)

    @render_widget
    def plot():
        n = counter.get()
        return (
            alt.Chart(
                pd.DataFrame(
                    {"x": [1, 2, 3], "y": [n, n + 1, n + 2]},
                )
            )
            .mark_line(point=True)
            .encode(x="x:Q", y="y:Q")
            .properties(title=f"render {n}")
        )


app = App(app_ui, server)
