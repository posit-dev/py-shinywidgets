from __future__ import annotations

import io

import pandas as pd
import plotly.express as px
from shiny.express import render, ui
from shinywidgets import render_perspective

ui.page_opts(title="Read on demand: export filtered rows", fillable=True)

countries = px.data.gapminder().query("year == 2007").drop(columns=["year", "iso_num"])

with ui.layout_columns(col_widths=[9, 3]):
    with ui.card(full_screen=True):

        @render_perspective
        def grid():
            return countries

    with ui.card():
        ui.card_header("Export")
        ui.p("Filter the grid (drag a column into Where), then download -- no need to read filter() anywhere else first.")

        # filter() is live from the moment the viewer renders, whether or not
        # anything has read it yet, so this handler can read it cold, the
        # instant the user clicks download: no warm-up reader required.
        @render.download_button(filename="filtered_countries.csv", label="Download filtered rows as CSV")
        def download_csv():
            view = grid.widget.table.view(filter=grid.filter())
            cols = view.to_columns()
            view.delete()
            df = pd.DataFrame(cols).drop(columns=["index"], errors="ignore")
            buf = io.StringIO()
            df.to_csv(buf, index=False)
            yield buf.getvalue()
