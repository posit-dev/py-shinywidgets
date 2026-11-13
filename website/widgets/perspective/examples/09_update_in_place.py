from __future__ import annotations

import plotly.express as px
from shiny import reactive
from shiny.express import input, ui
from shinywidgets import render_perspective

ui.page_opts(title="Update in place", fillable=True)
ui.input_dark_mode(id="mode")

countries = px.data.gapminder().query("year == 2007").drop(columns=["year", "iso_num"])


@render_perspective
def grid():
    return countries


@reactive.effect
def _sync_theme():
    # Setting a trait on .widget pushes it to the live viewer over its comm:
    # whatever pivot/sort/filter the user already set stays, and Perspective's
    # multi-megabyte ESM bundle isn't re-sent. Re-running grid() instead would
    # rebuild the viewer from scratch and lose both.
    grid.widget.theme = "Pro Dark" if input.mode() == "dark" else "Pro Light"
