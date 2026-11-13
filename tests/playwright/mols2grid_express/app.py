from __future__ import annotations

import ast
import os

# Expose window.__mols2grid__[name] (list.js instance etc.) for the tests
os.environ["M2G_DEBUG"] = "1"

import pandas as pd
from shiny import render
from shiny.express import ui
from shinywidgets import reactive_read, render_mols2grid

df = pd.DataFrame(
    {
        "SMILES": [
            "CCO",
            "c1ccccc1",
            "CCC(C)CC",
            "CC(=O)O",
            "COC",
            "CCN",
        ],
        "ID": [f"mol-{i}" for i in range(6)],
    }
)

ui.h2("mols2grid in Express")


@render_mols2grid(subset=["ID"], tooltip=["ID"], n_items_per_page=6)
def grid():
    return df


@render.text
def selection():
    # The selection trait is a repr string ({0: "CCO"}), not JSON
    sel = ast.literal_eval(reactive_read(grid.grid.widget, "selection"))
    return str(sel)
