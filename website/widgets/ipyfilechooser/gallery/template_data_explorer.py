# Title: Data file explorer
# One-line description: Pick a CSV from a sandboxed data directory and preview
#   it as a table and a plot -- an adaptable starting point for "browse the
#   server's data directory" apps.
# Bucket: template
# Run with: uv run --with 'shinywidgets[ipyfilechooser,itables,plotly]' shiny run template_data_explorer.py
# Data source: plotly.express.data (gapminder, tips) written to a sandboxed temp directory

import os
import tempfile

import pandas as pd
import plotly.express as px
from ipyfilechooser import FileChooser
from shiny import reactive, render, req
from shiny.express import ui
from shinywidgets import render_ipyfilechooser, render_itables, render_plotly


def make_data_dir() -> str:
    data_dir = tempfile.mkdtemp(prefix="shinywidgets-explorer-")
    px.data.gapminder().to_csv(os.path.join(data_dir, "gapminder.csv"), index=False)
    px.data.tips().to_csv(os.path.join(data_dir, "tips.csv"), index=False)
    return data_dir


DATA_DIR = make_data_dir()

ui.page_opts(title="Data file explorer", fillable=True)

picked_path = reactive.value(None)

with ui.sidebar(width=300):
    ui.markdown("Pick a CSV from the sandboxed `data/` directory.")

    @render_ipyfilechooser
    def picker():
        fc = FileChooser(path=DATA_DIR, sandbox_path=DATA_DIR, filter_pattern=["*.csv"])
        fc.register_callback(lambda fc: picked_path.set(fc.selected))
        return fc


@reactive.calc
def data():
    req(picked_path())
    return pd.read_csv(picked_path())


with ui.layout_columns(col_widths=(6, 6)):
    with ui.card(full_screen=True):
        ui.card_header("Table")

        @render_itables
        def table():
            return data()

    with ui.card(full_screen=True):
        ui.card_header("Plot")

        @render_plotly
        def plot():
            df = data()
            if "lifeExp" in df.columns:
                return px.scatter(
                    df, x="gdpPercap", y="lifeExp", size="pop", color="continent",
                    log_x=True, hover_name="country", animation_frame="year",
                )
            return px.histogram(df, x="total_bill", color="sex")
