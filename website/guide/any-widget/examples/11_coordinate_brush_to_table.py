import numpy as np
import pandas as pd
from shiny import reactive
from shiny.express import render, ui
from shinywidgets import render_widget

from sparkline_widget import Sparkline

rng = np.random.default_rng(5)
values = rng.normal(size=60).cumsum()
df = pd.DataFrame({"day": range(len(values)), "value": values})

ui.page_opts(title="Custom widget brush -> filtered table", fillable=True)
ui.markdown("Drag across the sparkline to select a range of days.")

with ui.layout_columns(col_widths=[7, 5]):
    with ui.card():
        ui.card_header("Sparkline -- drag to brush a range")

        @render_widget
        def spark():
            return Sparkline(values=list(values))

        # The widget's own `brush` reports [start_index, end_index]; feed it
        # right back in as `highlight` so the brushed range stays visibly
        # marked on the SAME widget (in place -- see "Updating the widget
        # from Python"), not just reflected in the table on the right.
        @reactive.effect
        def _mark_brush():
            lo, hi = spark.read("brush") or (0, -1)
            spark.widget.highlight = list(range(lo, hi + 1))

    with ui.card(full_screen=True):
        ui.card_header("Rows inside the brushed range")

        @render.data_frame
        def filtered():
            brush = spark.read("brush")
            if not brush:
                return render.DataGrid(df.iloc[0:0])
            lo, hi = brush
            return render.DataGrid(df.iloc[lo : hi + 1])
