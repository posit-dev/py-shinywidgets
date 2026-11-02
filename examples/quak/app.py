import numpy as np
import pandas as pd
from shiny import App, render, ui
from shinywidgets import output_widget, render_quak

rng = np.random.default_rng(0)
n = 5000
df = pd.DataFrame(
    {
        "species": rng.choice(["Adelie", "Chinstrap", "Gentoo"], n),
        "island": rng.choice(["Biscoe", "Dream", "Torgersen"], n),
        "bill_length_mm": rng.normal(44, 5, n).round(1),
        "body_mass_g": rng.normal(4200, 800, n).round(),
        "year": rng.integers(2007, 2010, n),
    }
)

app_ui = ui.page_fillable(
    ui.layout_columns(
        ui.card(
            ui.card_header("Sort columns and brush the histograms to filter"),
            output_widget("table"),
            full_screen=True,
        ),
        ui.card(
            ui.card_header("Current query"),
            ui.output_text_verbatim("sql"),
            ui.card_header("Matching rows"),
            ui.output_data_frame("matching"),
        ),
        col_widths=[8, 4],
    ),
    title="quak data table",
)


def server(input, output, session):
    @render_quak
    def table():
        return df

    @render.text
    def sql():
        return table.sql()

    @render.data_frame
    def matching():
        # Re-runs (debounced) whenever the query changes, evaluating it in
        # DuckDB. table.sql() cancels while the query is briefly empty during
        # startup, so no req() guard is needed.
        return render.DataGrid(table.data().df().head(100))


app = App(app_ui, server)
