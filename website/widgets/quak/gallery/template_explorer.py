# quak data explorer template
# A drop-in starting point: a DataFrame-backed table with column histograms,
# plus the current query and a live row count read back from the table.
# bucket: template
# run: uv run --no-sync shiny run docs/widget-guides/quak/gallery/template_explorer.py
# data: plotly.express.data.gapminder() (bundled with plotly)

from __future__ import annotations

import plotly.express as px
from shiny.express import render, ui
from shinywidgets import render_quak

ui.page_opts(title="Data explorer", fillable=True)

gapminder = px.data.gapminder()

with ui.layout_columns(col_widths=[8, 4], fill=False):
    ui.markdown(
        "Sort a column from its header, or drag across a numeric histogram "
        "(click a categorical bar) to filter. Drag again on the same "
        "histogram to narrow further; use **Reset** in the status bar to "
        "clear."
    )

with ui.layout_columns(col_widths=[8, 4]):
    with ui.card(full_screen=True):
        ui.card_header("gapminder: country-year observations")

        @render_quak
        def table():
            return gapminder

    with ui.card():
        ui.card_header("Matching rows")

        @render.text
        def n_rows():
            return f"{table.data().aggregate('count(*)').fetchall()[0][0]:,} of {len(gapminder):,}"

        ui.card_header("Current query")

        @render.code
        def sql():
            return table.sql()
