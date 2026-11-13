from __future__ import annotations

from typing import Any, Dict, Optional

import plotly.express as px
from shiny import reactive
from shiny.express import input, ui
from shinywidgets import render_perspective

ui.page_opts(title="Save and restore a view", fillable=True)
ui.input_action_button("save", "Save this view")
ui.input_action_button("restore", "Restore saved view")

countries = px.data.gapminder().query("year == 2007").drop(columns=["year", "iso_num"])

saved_view: reactive.Value[Optional[Dict[str, Any]]] = reactive.value(None)


@render_perspective
def grid():
    return countries


@reactive.effect
@reactive.event(input.save)
def _():
    # .widget.save() captures the full viewer config -- pivot, sort, filter,
    # plugin, theme, columns_config, everything -- as a plain dict. Store it
    # anywhere: a reactive.value, a file, a database row.
    saved_view.set(grid.widget.save())


@reactive.effect
@reactive.event(input.restore)
def _():
    cfg = saved_view.get()
    if cfg is not None:
        grid.widget.restore(**cfg)
