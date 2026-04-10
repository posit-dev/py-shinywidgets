from __future__ import annotations

import altair as alt
from shiny import App, reactive, render, ui
from shinywidgets import output_widget, render_widget

app_ui = ui.page_fluid(
    ui.input_action_button("rerender", "Rerender"),
    ui.output_text("render_count"),
    output_widget("plot"),
)


def server(input, output, session):
    counter = reactive.value(0)

    @reactive.effect
    @reactive.event(input.rerender)
    def _():
        counter.set(counter.get() + 1)

    @render.text
    def render_count():
        return str(counter.get())

    @render_widget
    def plot():
        n = counter.get()
        return (
            alt.Chart(
                alt.Data(
                    values=[
                        {"x": 1, "y": n},
                        {"x": 2, "y": n + 1},
                        {"x": 3, "y": n + 2},
                    ]
                )
            )
            .mark_line(point=True)
            .encode(x="x:Q", y="y:Q")
            .properties(title=f"render {n}")
        )


app = App(app_ui, server)
