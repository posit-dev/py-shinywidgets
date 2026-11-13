from __future__ import annotations

import mols2grid
import pandas as pd
import plotly.express as px
from rdkit import Chem
from rdkit.Chem import Descriptors
from shiny import reactive
from shiny.express import ui
from shinywidgets import render_mols2grid, render_plotly


def load_molecules() -> pd.DataFrame:
    df = mols2grid.sdf_to_dataframe(mols2grid.datafiles.SOLUBILITY_SDF)
    df = df[["SMILES", "ID"]].reset_index(drop=True)
    mw, logp = [], []
    for smiles in df["SMILES"]:
        mol = Chem.MolFromSmiles(smiles)
        mw.append(round(Descriptors.MolWt(mol), 1) if mol else float("nan"))
        logp.append(round(Descriptors.MolLogP(mol), 2) if mol else float("nan"))
    df["MW"], df["LogP"] = mw, logp
    return df.dropna(subset=["MW"]).reset_index(drop=True)


MOLS = load_molecules()

ui.page_opts(title="mols2grid + plotly: lasso to filter the grid", fillable=True)

with ui.layout_columns(col_widths=[5, 7]):
    with ui.card(full_screen=True):
        ui.card_header("Lasso- or box-select points")

        @render_plotly
        def scatter():
            fig = px.scatter(MOLS, x="MW", y="LogP", custom_data=[MOLS.index])
            fig.update_layout(dragmode="lasso")
            return fig

    with ui.card(full_screen=True):
        ui.card_header("Grid filtered to the selection")

        @render_mols2grid(subset=["ID"], tooltip=["ID", "MW", "LogP"])
        def grid():
            return MOLS


@reactive.effect
def _link():
    if grid.grid is None or scatter.selected() is None:
        return  # nothing lassoed yet: leave every molecule visible
    selected = scatter.selected_rows(MOLS)
    mask = MOLS.index.isin(selected.index)
    grid.grid.filter(mask.tolist())
