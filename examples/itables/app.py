import numpy as np
import pandas as pd
from itables.widget import ITable
from shiny import App, render, ui
from shinywidgets import output_widget, reactive_read, render_itables

rng = np.random.default_rng(1)

cars = pd.DataFrame(
    {
        "model": [f"Car {i + 1}" for i in range(300)],
        "weight": rng.uniform(1.5, 5.0, 300).round(2),
    }
)
cars["mpg"] = (45 - 6 * cars["weight"] + rng.normal(0, 2.5, 300)).round(1)
cars["hp"] = (40 * cars["weight"] + rng.normal(0, 25, 300)).round()

app_ui = ui.page_fillable(
    ui.layout_columns(
        ui.card(
            ui.card_header("Click rows to select them (Ctrl/Cmd-click for several)"),
            output_widget("table"),
            full_screen=True,
        ),
        ui.card(
            ui.card_header("Selected rows, as seen by Python"),
            ui.output_data_frame("selected"),
        ),
        col_widths=[8, 4],
    ),
)


def server(input, output, session):
    @render_itables
    def table():
        # Return an ITable (rather than a data frame) to pass itables options. The
        # table fills its card and scrolls, even in full screen mode.
        return ITable(cars, select=True, paging=False)

    @render.data_frame
    def selected():
        rows = reactive_read(table.widget, "selected_rows")
        return cars.iloc[rows]


app = App(app_ui, server)
