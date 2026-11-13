from __future__ import annotations

import plotly.express as px
from shiny.express import render, ui
from shinywidgets import render_perspective

ui.page_opts(title="Filtered summary", fillable=True)

countries = px.data.gapminder().query("year == 2007").drop(columns=["year", "iso_num"])

with ui.layout_columns(col_widths=[9, 3]):
    with ui.card(full_screen=True):

        @render_perspective
        def grid():
            return countries

    with ui.card():
        ui.card_header("Exactly what's visible")

        @render.text
        def total():
            # view_config() carries the pivot/group/filter the user set in
            # the browser; replay it server-side so the total always matches
            # the rows on screen. Drop "plugin": it's how rows are drawn,
            # not which ones.
            cfg = {k: v for k, v in grid.view_config().items() if k != "plugin"}
            view = grid.widget.table.view(**cfg)
            cols = view.to_columns()
            view.delete()
            if "__ROW_PATH__" in cols:
                # Grouped views put a grand total in the first row (its
                # __ROW_PATH__ is []); summing every row would double-count it.
                pop = cols["pop"][0]
                rows = len(cols["__ROW_PATH__"]) - 1
            else:
                pop = sum(cols.get("pop", []))
                rows = len(cols.get("country", cols.get("pop", [])))
            return f"{rows} rows\n{pop:,.0f} people"
