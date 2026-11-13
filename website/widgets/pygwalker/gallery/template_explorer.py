# PyGWalker starting point: a drag-and-drop explorer over a filtered dataframe,
# with the DuckDB lockdown render_pygwalker requires. Template: ~50 lines,
# adapt by swapping `tips` for your own dataframe and the filter for yours.
# Run: uv run --no-sync shiny run docs/widget-guides/pygwalker/gallery/template_explorer.py
# Data: plotly.express.data.tips() (ships with plotly)
import duckdb
import plotly.express as px
import pygwalker
from shiny.express import input, ui

from shinywidgets import render_pygwalker

# Single-file version of the lockdown in ../examples/globals.py: guarded so it
# tolerates Shiny Express re-running this file more than once per process
# (lock_configuration can only be set once; setting it again raises). In a
# multi-file app, put this in a sibling globals.py instead (see the guide).
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

ui.page_opts(title="Tips explorer", fillable=True)

tips = px.data.tips()

with ui.sidebar():
    ui.input_select(
        "day", "Day", choices=["All", *sorted(tips["day"].unique())], selected="All"
    )
    ui.input_select(
        "time", "Time", choices=["All", *sorted(tips["time"].unique())], selected="All"
    )

with ui.card(full_screen=True):

    @render_pygwalker
    def explorer():
        df = tips
        if input.day() != "All":
            df = df[df["day"] == input.day()]
        if input.time() != "All":
            df = df[df["time"] == input.time()]
        return df
