import numpy as np
import pandas as pd
from jscatter import Scatter
from shiny import reactive, req
from shiny.express import render, ui
from shinywidgets import render_jscatter

rng = np.random.default_rng(6)
cars = pd.DataFrame(
    {
        "model": [f"Car {i}" for i in range(60)],
        "weight": rng.uniform(1.8, 4.5, 60).round(2),
        "mpg": rng.uniform(14, 44, 60).round(1),
    }
)

ui.page_opts(title="Table row selection highlights the plot", fillable=True)

with ui.layout_columns():
    with ui.card(full_screen=True):

        @render.data_frame
        def table():
            return render.DataGrid(cars, selection_mode="rows")

    with ui.card(full_screen=True):

        @render_jscatter
        def plot():
            return Scatter(data=cars, x="weight", y="mpg")

        @reactive.effect
        def _highlight():
            rows = table.cell_selection()["rows"]
            w = plot.widget
            req(w)
            ids = np.array(rows, dtype="uint32")
            with reactive.isolate():
                w.selection = ids
