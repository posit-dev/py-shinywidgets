from __future__ import annotations

import pandas as pd
import plotly.express as px
from shiny.express import ui
from shinywidgets import render_perspective, render_plotly

ui.page_opts(title="Perspective filter -> plotly chart", fillable=True)

countries = px.data.gapminder().query("year == 2007").drop(columns=["year", "iso_num"])

with ui.layout_columns():

    @render_perspective
    def grid():
        return countries

    @render_plotly
    def chart():
        # Replay the user's filter (set in the viewer's settings panel)
        # server-side and chart exactly those rows by continent. Drop
        # "group_by": the raw rows are re-aggregated here in pandas instead.
        cfg = {
            k: v
            for k, v in grid.view_config().items()
            if k not in ("plugin", "group_by")
        }
        view = grid.widget.table.view(**cfg)
        cols = view.to_columns()
        view.delete()
        df = pd.DataFrame({"continent": cols["continent"], "pop": cols["pop"]})
        totals = df.groupby("continent", as_index=False)["pop"].sum()
        return px.bar(
            totals, x="continent", y="pop", title="Population by continent (filtered)"
        )
