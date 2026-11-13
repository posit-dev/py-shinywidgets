import os
import tempfile

import pandas as pd
import plotly.express as px
from ipyfilechooser import FileChooser
from shiny import reactive, render, req
from shiny.express import ui
from shinywidgets import render_ipyfilechooser, render_itables, render_plotly


def make_data_dir() -> str:
    """A small sandboxed data directory: two CSVs plus a decoy text file."""
    data_dir = tempfile.mkdtemp(prefix="shinywidgets-preview-")
    gapminder = px.data.gapminder()
    gapminder[gapminder["year"] == 2007].to_csv(
        os.path.join(data_dir, "gapminder_2007.csv"), index=False
    )
    px.data.tips().to_csv(os.path.join(data_dir, "tips.csv"), index=False)
    with open(os.path.join(data_dir, "README.txt"), "w") as f:
        f.write("Only *.csv files are selectable here (see filter_pattern).\n")
    return data_dir


DATA_DIR = make_data_dir()

ui.page_opts(title="Pick a CSV, preview it", fillable=True)

picked_path = reactive.value(None)

with ui.sidebar(width=320):

    @render_ipyfilechooser
    def picker():
        fc = FileChooser(path=DATA_DIR, sandbox_path=DATA_DIR, filter_pattern=["*.csv"])
        fc.register_callback(lambda fc: picked_path.set(fc.selected))
        return fc


@reactive.calc
def df():
    req(picked_path())
    return pd.read_csv(picked_path())


with ui.layout_columns(col_widths=(6, 6)):
    with ui.card(full_screen=True):
        ui.card_header("Table")

        @render_itables
        def table():
            return df()

    with ui.card(full_screen=True):
        ui.card_header("Plot")

        @render_plotly
        def plot():
            data = df()
            if "lifeExp" in data.columns:
                return px.scatter(
                    data, x="gdpPercap", y="lifeExp", size="pop", color="continent",
                    log_x=True, hover_name="country",
                )
            return px.histogram(data, x="total_bill", color="sex")
