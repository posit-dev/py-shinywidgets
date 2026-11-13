import pandas as pd
import plotly.express as px
import pygwalker
from shiny import reactive
from shiny.express import ui

import globals  # noqa: F401 -- locks down DuckDB once per process; see globals.py
from shinywidgets import render_plotly, render_pygwalker

ui.page_opts(fillable=True)

tips = px.data.tips()
exported = reactive.value(None)

with ui.layout_columns(col_widths=[7, 5]):
    with ui.card(full_screen=True):
        ui.card_header("Build a chart, then click the export icon")

        @render_pygwalker
        def explorer():
            return tips

        @reactive.effect
        def _capture_export():
            def on_msg(widget, content, buffers):
                if content.get("type") != "pyg_request":
                    return
                if content["msg"]["action"].startswith("export_dataframe"):
                    exported.set(pygwalker.GlobalVarManager.last_exported_dataframe)

            explorer.widget.on_msg(on_msg)

    with ui.card(full_screen=True):
        ui.card_header("The same computed rows, as a plotly bar chart")

        @render_plotly
        def bar():
            df = exported.get()
            if df is None:
                return px.bar(title="Export a chart to see it here")
            num_col = next(c for c in df.columns if pd.api.types.is_numeric_dtype(df[c]))
            cat_col = next(c for c in df.columns if c != num_col)
            return px.bar(df, x=cat_col, y=num_col, title=f"{num_col} by {cat_col}")
