import json

import pandas as pd
import plotly.express as px
import pygwalker
from shiny import reactive
from shiny.express import render, ui

import globals  # noqa: F401 -- locks down DuckDB once per process; see globals.py
from shinywidgets import render_pygwalker

ui.page_opts(fillable=True)

tips = px.data.tips()

saved_spec = reactive.value(None)
exported = reactive.value(None)

with ui.layout_columns(col_widths=[8, 4]):
    with ui.card(full_screen=True):

        @render_pygwalker
        def explorer():
            return tips

    with ui.card():
        ui.card_header("What Python saw")

        @reactive.effect
        def _register_on_msg():
            def on_msg(widget, content, buffers):
                if content.get("type") != "pyg_request":
                    return
                msg = content["msg"]
                if msg["action"] == "update_spec":  # Ctrl/Cmd+S
                    saved_spec.set(msg["data"]["visSpec"])
                elif msg["action"].startswith("export_dataframe"):  # export icon
                    exported.set(pygwalker.GlobalVarManager.last_exported_dataframe)

            explorer.widget.on_msg(on_msg)

        ui.markdown("Press **Ctrl/Cmd+S** in the explorer: its saved encodings land here.")

        @render.code
        def spec_summary():
            spec = saved_spec.get()
            if spec is None:
                return "(not saved yet)"
            encodings = spec[0]["encodings"]
            used = {
                shelf: [f["name"] for f in fields]
                for shelf, fields in encodings.items()
                if fields and shelf in ("columns", "rows", "color")
            }
            return json.dumps(used, indent=2)

        ui.markdown("Click the export icon: the chart's computed rows land here.")

        @render.data_frame
        def exported_table():
            df = exported.get()
            if df is None:
                return render.DataGrid(pd.DataFrame({"status": ["(not exported yet)"]}))
            return render.DataGrid(df)
