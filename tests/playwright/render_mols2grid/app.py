from __future__ import annotations

import ast
import os

# Expose window.__mols2grid__[name] (list.js instance etc.) for the tests
os.environ["M2G_DEBUG"] = "1"

import pandas as pd
from shiny import App, reactive, render, ui
from shinywidgets import output_widget, reactive_read, render_mols2grid

df = pd.DataFrame(
    {
        "SMILES": [
            "CCO",
            "c1ccccc1",
            "CCC(C)CC",
            "CC(=O)O",
            "COC",
            "CCN",
            "CO",
            "C",
            "CC",
            "CCC",
            "CCCC",
            "CCCCC",
        ],
        "ID": [f"mol-{i}" for i in range(12)],
        "MW": [46.1, 78.1, 72.2, 60.1, 46.1, 45.1, 32.0, 16.0, 30.1, 44.1, 58.1, 72.2],
    }
)

app_ui = ui.page_fluid(
    ui.input_action_button("rerender", "Rerender"),
    ui.input_action_button("filter", "Filter MW < 50"),
    ui.input_checkbox("show_grid2", "Show second grid", False),
    ui.output_ui("grid2_container"),
    ui.output_text("render_count"),
    ui.output_text("selection"),
    ui.card(output_widget("grid"), height="650px"),
)


def server(input, output, session):
    counter = reactive.value(0)

    @reactive.effect
    @reactive.event(input.rerender)
    def _():
        counter.set(counter.get() + 1)

    @render.text
    def render_count():
        return str(counter.get())

    @render_mols2grid(subset=["ID"], tooltip=["ID"], n_items_per_page=12)
    def grid():
        counter.get()
        return df

    @render.text
    def selection():
        # The selection trait is a repr string ({0: "CCO"}), not JSON
        sel = ast.literal_eval(reactive_read(grid.grid.widget, "selection"))
        return str(sel)

    @reactive.effect
    @reactive.event(input.filter)
    def _filter():
        if grid.grid is not None:
            grid.grid.filter((df["MW"] < 50).tolist())

    # A second grid with a distinct output id (hence a distinct grid name), to
    # exercise browser-global cleanup when a grid output comes and goes
    @render.ui
    def grid2_container():
        if input.show_grid2():
            return ui.card(output_widget("grid2"), height="650px")

    @render_mols2grid(subset=["ID"], tooltip=["ID"], n_items_per_page=12)
    def grid2():
        return df


app = App(app_ui, server)
