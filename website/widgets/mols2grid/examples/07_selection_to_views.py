from __future__ import annotations

import io

import mols2grid
import pandas as pd
import plotly.express as px
from rdkit import Chem
from rdkit.Chem import Descriptors
from shiny import render
from shiny.express import ui
from shinywidgets import render_mols2grid, render_plotly


def load_molecules() -> pd.DataFrame:
    df = mols2grid.sdf_to_dataframe(mols2grid.datafiles.SOLUBILITY_SDF)
    df = df[["SMILES", "ID", "SOL"]].rename(columns={"SOL": "LogS"})
    df["MW"] = [
        round(Descriptors.MolWt(m), 1) if (m := Chem.MolFromSmiles(s)) else None
        for s in df["SMILES"]
    ]
    return df.dropna(subset=["MW"]).reset_index(drop=True)


MOLS = load_molecules()

ui.page_opts(title="mols2grid: selection -> table, chart, download", fillable=True)

with ui.layout_columns(col_widths=[7, 5]):
    with ui.card(full_screen=True):
        ui.card_header("Pick some molecules")

        @render_mols2grid(subset=["ID"], tooltip=["ID", "MW", "LogS"])
        def grid():
            return MOLS

    with ui.layout_columns(col_widths=12):
        with ui.card():
            ui.card_header("Selected molecules")

            @render.data_frame
            def table():
                return render.DataGrid(selected_rows(), width="100%")

            @render.download_button(
                filename="selected_molecules.sdf", label="Download selection as SDF"
            )
            def download():
                writer_out = io.StringIO()
                writer = Chem.SDWriter(writer_out)
                for smiles, id_ in zip(selected_rows()["SMILES"], selected_rows()["ID"]):
                    mol = Chem.MolFromSmiles(smiles)
                    if mol is not None:
                        mol.SetProp("_Name", str(id_))
                        writer.write(mol)
                writer.close()
                yield writer_out.getvalue()

        with ui.card():
            ui.card_header("Molecular weight of the selection")

            @render_plotly
            def hist():
                return px.histogram(selected_rows(), x="MW", nbins=10)


def selected_rows() -> pd.DataFrame:
    # Positional row indices from the browser, looked up directly in MOLS
    # (the same frame and row order the grid was built from)
    idx = [int(k) for k in (grid.selected() or {})]
    return MOLS.loc[idx]
