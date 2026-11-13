# PyGWalker showcase: a filterable explorer that keeps the user's saved chart
# across filter changes, plus a value box and table built from whatever the
# user exports. Showcase: ~130 lines.
# Run: uv run --no-sync shiny run docs/widget-guides/pygwalker/gallery/showcase_tips_dashboard.py
# Data: plotly.express.data.tips() (ships with plotly)
import json

import duckdb
import pandas as pd
import plotly.express as px
import pygwalker
from pygwalker.api.anywidget import walk
from shiny import reactive
from shiny.express import input, render, ui

from shinywidgets import render_pygwalker


def _lockdown_once() -> None:
    pygwalker.GlobalVarManager.set_privacy("offline")
    locked = duckdb.execute(
        "SELECT current_setting('lock_configuration')"
    ).fetchone()[0]
    if not locked:
        duckdb.execute("SET TimeZone = 'UTC'")
        duckdb.execute("SET enable_external_access = false")
        duckdb.execute("SET lock_configuration = true")


_lockdown_once()

ui.page_opts(title="Tips dashboard", fillable=True)

tips = px.data.tips()
saved_spec = reactive.value(None)
exported = reactive.value(None)

with ui.sidebar():
    ui.input_select(
        "day", "Day", choices=["All", *sorted(tips["day"].unique())], selected="All"
    )
    ui.input_checkbox_group(
        "smoker", "Smoker", choices=["Yes", "No"], selected=["Yes", "No"]
    )
    ui.markdown(
        "Build a chart, then **Ctrl/Cmd+S** to keep it across filter changes. "
        "Click the export icon to fill the summary below."
    )

with ui.layout_columns(col_widths=[8, 4]):
    with ui.card(full_screen=True):
        ui.card_header("Explorer")

        @render_pygwalker
        def explorer():
            df = tips
            if input.day() != "All":
                df = df[df["day"] == input.day()]
            df = df[df["smoker"].isin(input.smoker())]
            with reactive.isolate():
                spec = saved_spec.get()
            return walk(df, spec=json.dumps(spec) if spec else "")

        @reactive.effect
        def _on_msg():
            def handler(widget, content, buffers):
                if content.get("type") != "pyg_request":
                    return
                msg = content["msg"]
                if msg["action"] == "update_spec":
                    saved_spec.set(msg["data"]["visSpec"])
                elif msg["action"].startswith("export_dataframe"):
                    exported.set(pygwalker.GlobalVarManager.last_exported_dataframe)

            explorer.widget.on_msg(handler)

    with ui.card(full_screen=True):
        ui.card_header("Exported summary")

        @render.ui
        def summary_box():
            df = exported.get()
            if df is None:
                return ui.p(
                    "Export a chart to see its computed rows here.",
                    class_="text-muted",
                )
            num_col = next(
                c for c in df.columns if pd.api.types.is_numeric_dtype(df[c])
            )
            return ui.value_box(
                f"Total {num_col}",
                f"{df[num_col].sum():,.2f}",
                showcase=None,
            )

        @render.data_frame
        def exported_table():
            df = exported.get()
            if df is None:
                return render.DataGrid(pd.DataFrame({"status": ["(not exported yet)"]}))
            return render.DataGrid(df)
