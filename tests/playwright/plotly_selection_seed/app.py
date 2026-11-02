from __future__ import annotations

import pandas as pd
import plotly.express as px
from shiny import App, reactive, render, ui
from shinywidgets import output_widget, render_plotly

# The accessor reads the tests assert on are gated behind an action button,
# so nothing consumer-facing reads them at startup. A selection made before
# the button click exercises the eager state attach and the seed on bridge
# bind (see the tests and REPORT.md).

df = pd.DataFrame({"x": [1, 2, 3, 4, 5], "y": [1, 4, 9, 16, 25], "g": list("aabbb")})

app_ui = ui.page_fluid(
    ui.input_action_button("read_selection", "Read selection"),
    ui.output_text("selected"),
    ui.output_text("selected_rows"),
    ui.output_text("brushed"),
    ui.output_text("synced_selection"),
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

    # Sentinel: an ungated read of the same accessor state, so a test can
    # wait until a gesture has synced from browser to server before
    # triggering a gated read. plotly.js emits plotly_selected a few hundred
    # ms after mouseup, so without this a button click right after the drag
    # can overtake the selection message.
    @render.text
    def synced_selection():
        pts = plot.selected()
        return "None" if pts is None else str(len(pts))


app = App(app_ui, server)
