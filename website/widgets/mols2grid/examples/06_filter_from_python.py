from __future__ import annotations

import mols2grid
import pandas as pd
from rdkit import Chem
from rdkit.Chem import Descriptors
from shiny import reactive
from shiny.express import input, ui

from shinywidgets import render_mols2grid

ui.page_opts(title="mols2grid: filter from Python", fillable=True)


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

mw_lo, mw_hi = float(MOLS["MW"].min()), float(MOLS["MW"].max())
logp_lo, logp_hi = float(MOLS["LogP"].min()), float(MOLS["LogP"].max())

with ui.sidebar():
    ui.input_slider("mw", "Molecular weight", min=mw_lo, max=mw_hi, value=(mw_lo, mw_hi))
    ui.input_slider("logp", "LogP", min=logp_lo, max=logp_hi, value=(logp_lo, logp_hi))

with ui.card(full_screen=True):

    @render_mols2grid(subset=["ID"], tooltip=["ID", "MW", "LogP"])
    def grid():
        # Runs once: the sliders filter the already-rendered grid below
        # instead of re-running this function, so the grid document (and its
        # ~50 KB+ of boilerplate HTML) isn't re-sent on every drag.
        return MOLS


@reactive.effect
def _filter():
    # grid.grid is None until the first render; filter() updates the
    # browser's list.js view in place without rebuilding the iframe, so
    # pagination/sort/search state (and any selection) survives.
    if grid.grid is None:
        return
    lo, hi = input.mw()
    plo, phi = input.logp()
    mask = MOLS["MW"].between(lo, hi) & MOLS["LogP"].between(plo, phi)
    grid.grid.filter(mask.tolist())
