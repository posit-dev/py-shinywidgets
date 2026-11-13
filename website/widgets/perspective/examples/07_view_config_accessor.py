from __future__ import annotations

import plotly.express as px
from shiny.express import render, ui
from shinywidgets import render_perspective

ui.page_opts(title="view_config() accessor", fillable=True)

countries = px.data.gapminder().query("year == 2007").drop(columns=["year", "iso_num"])


@render_perspective
def grid():
    return countries


@render.code
def config_state():
    # The structural subset of the viewer's config: plugin, columns,
    # group_by, split_by, aggregates, sort, filter, expressions. Cosmetic
    # changes (opening settings, switching themes) don't fire this.
    cfg = grid.view_config()
    return "\n".join(f"{k}: {v}" for k, v in cfg.items())
