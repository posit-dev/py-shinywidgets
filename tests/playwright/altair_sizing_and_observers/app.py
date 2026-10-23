from __future__ import annotations

import altair as alt
from shiny import App, reactive, render, ui
from shinywidgets import output_widget, render_altair

data = alt.Data(values=[{"x": i, "y": i * i} for i in range(20)])

app_ui = ui.page_fluid(
    output_widget("fixed", height="300px"),
    output_widget("observed"),
    ui.output_text("brushes"),
)


def server(input, output, session):
    n_brushes = reactive.value(0)

    @render_altair
    def fixed():
        return alt.Chart(data).mark_point().encode(x="x:Q", y="y:Q")

    @render_altair
    def observed():
        brush = alt.selection_interval(name="brush")
        chart = alt.Chart(data).mark_point().encode(x="x:Q", y="y:Q").add_params(brush)
        jchart = alt.JupyterChart(chart)

        # The idiom altair documents for reacting to selections
        def on_brush(change):
            n_brushes.set(n_brushes.get() + 1)

        jchart.selections.observe(on_brush, ["brush"])
        return jchart

    @render.text
    def brushes():
        return f"brushes: {n_brushes()}"


app = App(app_ui, server)
