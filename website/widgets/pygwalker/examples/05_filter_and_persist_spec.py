import json

import plotly.express as px
from pygwalker.api.anywidget import walk
from shiny import reactive
from shiny.express import input, ui

import globals  # noqa: F401 -- locks down DuckDB once per process; see globals.py
from shinywidgets import render_pygwalker

ui.page_opts(fillable=True)

tips = px.data.tips()
saved_spec = reactive.value(None)

ui.input_select(
    "day", "Day", choices=["All", *sorted(tips["day"].unique())], selected="All"
)
ui.markdown(
    "Build a chart, then press **Ctrl/Cmd+S**. Switching the day filter re-renders "
    "the explorer with the filtered data -- and replays the saved chart on it."
)


@render_pygwalker
def explorer():
    day = input.day()
    df = tips if day == "All" else tips[tips["day"] == day]
    with reactive.isolate():
        spec = saved_spec.get()
    return walk(df, spec=json.dumps(spec) if spec else "")


@reactive.effect
def _capture_spec():
    def on_msg(widget, content, buffers):
        if content.get("type") != "pyg_request":
            return
        if content["msg"]["action"] == "update_spec":
            saved_spec.set(content["msg"]["data"]["visSpec"])

    explorer.widget.on_msg(on_msg)
