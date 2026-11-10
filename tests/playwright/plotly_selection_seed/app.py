from __future__ import annotations

import pandas as pd
import plotly.express as px
from shiny import App, reactive, render, ui
from shinywidgets import output_widget, render_plotly

# The accessor reads the tests assert on are gated behind an action button,
# and NOTHING reads them at startup (an ungated read would attach the
# accessor early, defeating the scenario). A selection made before the
# button click exercises the eager state attach and the seed on bridge bind
# (see the tests).

df = pd.DataFrame({"x": [1, 2, 3, 4, 5], "y": [1, 4, 9, 16, 25], "g": list("aabbb")})

app_ui = ui.page_fluid(
    ui.input_action_button("read_selection", "Read selection"),
    ui.output_text("selected"),
    ui.output_text("selected_rows"),
    ui.output_text("brushed"),
    ui.card(output_widget("plot"), height="450px"),
)


def server(input, output, session):
    @render_plotly
    def plot():
        fig = px.scatter(df, x="x", y="y", color="g", custom_data=[df.index])
        fig.update_traces(marker_size=14)
        fig.update_layout(dragmode="select")
        return fig

    @render.text
    @reactive.event(input.read_selection)
    def selected():
        pts = plot.selected()
        if pts is None:
            return "None"
        return ";".join(f"{r.trace_index},{r.point_index}" for r in pts.itertuples())

    @render.text
    @reactive.event(input.read_selection)
    def selected_rows():
        return ",".join(str(x) for x in plot.selected_rows(df)["x"])

    @render.text
    @reactive.event(input.read_selection)
    def brushed():
        b = plot.brushed()
        return "None" if b is None else ",".join(sorted(b))


app = App(app_ui, server)
