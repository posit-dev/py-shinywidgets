from __future__ import annotations

import duckdb
import pandas as pd
import pygwalker
from pygwalker.api.anywidget import walk
from shiny import App, reactive, render, ui
from shinywidgets import output_widget, render_pygwalker

# Keep the Python process from phoning home (update check, usage events)
pygwalker.GlobalVarManager.set_privacy("offline")

# The recommended DuckDB lockdown (see the render_pygwalker docstring)
duckdb.execute("SET TimeZone = 'UTC'")
duckdb.execute("SET enable_external_access = false")
duckdb.execute("SET lock_configuration = true")

df = pd.DataFrame(
    {
        "city": [f"city-{i}" for i in range(30)],
        "population": [1000 + 17 * i for i in range(30)],
    }
)

app_ui = ui.page_fluid(
    ui.input_action_button("rerender", "Rerender"),
    ui.output_text("render_count"),
    ui.output_text("request_count"),
    ui.card(output_widget("explorer"), id="fill_card", height="650px"),
    output_widget("explicit_height", height="480px"),
    output_widget("widget_height"),
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

    requests = reactive.value(0)

    @reactive.effect
    def _():
        explorer.widget.on_msg(count_request)

    def count_request(widget, content, buffers):
        if content.get("type") == "pyg_request":
            requests.set(requests.get() + 1)

    @render.text
    def request_count():
        return str(requests.get())

    @render_pygwalker
    def explorer():
        counter.get()
        return df

    @render_pygwalker
    def explicit_height():
        return df

    @render_pygwalker
    def widget_height():
        widget = walk(df)
        widget.layout.height = "420px"
        return widget


app = App(app_ui, server)
