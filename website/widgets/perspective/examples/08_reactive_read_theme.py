from __future__ import annotations

import plotly.express as px
from shiny.express import render, ui
from shinywidgets import render_perspective

ui.page_opts(title="Beyond the accessors: read()", fillable=True)

countries = px.data.gapminder().query("year == 2007 and continent == 'Europe'")


@render_perspective
def grid():
    return countries


@render.code
def cosmetic_state():
    # theme/title/settings don't change which rows are shown, so they're
    # outside view_config() -- read() falls through to reactive_read() on
    # the widget for any trait that isn't a declared accessor.
    return f"theme: {grid.read('theme')!r}\nsettings panel open: {grid.read('settings')}"
