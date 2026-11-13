import numpy as np
import pandas as pd
from shiny import reactive
from shiny.express import render, ui
from shinywidgets import render_widget

from sparkline_widget import Sparkline

rng = np.random.default_rng(6)
values = rng.normal(size=30).cumsum()
df = pd.DataFrame({"day": range(len(values)), "value": values.round(3)})

ui.page_opts(title="Table row selection -> custom widget highlight", fillable=True)

with ui.layout_columns(col_widths=[5, 7]):
    with ui.card(full_screen=True):
        ui.card_header("Select a row")

        @render.data_frame
        def table():
            return render.DataGrid(df, selection_mode="row")

    with ui.card():
        ui.card_header("The same row, highlighted in place on the sparkline")

        @render_widget
        def spark():
            return Sparkline(values=list(values))

        # Shiny's own render.data_frame accessor (.cell_selection()) drives a
        # widget that has nothing to do with tables: no re-render, just an
        # in-place trait write on the existing Sparkline instance.
        @reactive.effect
        def _sync_highlight():
            rows = table.cell_selection()["rows"]
            spark.widget.highlight = list(rows)
