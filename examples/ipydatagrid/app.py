import numpy as np
import pandas as pd
from ipydatagrid import DataGrid
from shiny import App, render, ui
from shinywidgets import output_widget, reactive_read, render_ipydatagrid

rng = np.random.default_rng(1)

cars = pd.DataFrame(
    {
        "model": [f"Car {i + 1}" for i in range(500)],
        "weight": rng.uniform(1.5, 5.0, 500).round(2),
    }
)
cars["mpg"] = (45 - 6 * cars["weight"] + rng.normal(0, 2.5, 500)).round(1)
cars["hp"] = (40 * cars["weight"] + rng.normal(0, 25, 500)).round()

app_ui = ui.page_fillable(
    ui.layout_columns(
        ui.card(
            ui.card_header("Click or drag to select rows; click a header to sort"),
            output_widget("grid"),
            full_screen=True,
        ),
        ui.card(
            ui.card_header("Selected rows"),
            ui.output_data_frame("selected"),
        ),
        col_widths=[8, 4],
    ),
)


def server(input, output, session):
    @render_ipydatagrid
    def grid():
        return DataGrid(cars, selection_mode="row")

    @render.data_frame
    def selected():
        selections = reactive_read(grid.widget, "selections")
        # Selections index into the rows as displayed, so use the grid's
        # (possibly sorted or filtered) view of the data
        visible = grid.widget.get_visible_data()
        rows = sorted({r for s in selections for r in range(s["r1"], s["r2"] + 1)})
        return render.DataGrid(visible.iloc[rows].reset_index(drop=True))


app = App(app_ui, server)
