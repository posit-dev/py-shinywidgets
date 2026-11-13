from __future__ import annotations

import matplotlib.pyplot as plt
import mols2grid
from rdkit import Chem
from rdkit.Chem import Descriptors, Draw
from shiny import render, req
from shiny.express import ui

from shinywidgets import render_mols2grid

ui.page_opts(title="mols2grid: click -> detail card", fillable=True)

mols = mols2grid.sdf_to_dataframe(mols2grid.datafiles.SOLUBILITY_SDF)

with ui.layout_columns(col_widths=[7, 5]):
    with ui.card(full_screen=True):
        ui.card_header("Click a molecule's image")

        @render_mols2grid(clicks=True, subset=["ID"], n_items_per_page=12)
        def grid():
            return mols

    with ui.card():
        ui.card_header("Detail card")

        @render.plot
        def depiction():
            row = grid.clicked()
            req(row is not None)
            mol = Chem.MolFromSmiles(row["SMILES"])
            fig, ax = plt.subplots(figsize=(4, 3))
            ax.imshow(Draw.MolToImage(mol, size=(400, 300)))
            ax.axis("off")
            return fig

        @render.ui
        def descriptors():
            row = grid.clicked()
            if row is None:
                return ui.p("Click a molecule to see its descriptors.")
            mol = Chem.MolFromSmiles(row["SMILES"])
            rows = {
                "ID": row["ID"],
                "MW": f"{Descriptors.MolWt(mol):.1f}",
                "LogP": f"{Descriptors.MolLogP(mol):.2f}",
                "TPSA": f"{Descriptors.TPSA(mol):.1f}",
                "H-bond donors": Descriptors.NumHDonors(mol),
                "H-bond acceptors": Descriptors.NumHAcceptors(mol),
                "Rotatable bonds": Descriptors.NumRotatableBonds(mol),
            }
            return ui.tags.table(
                *[ui.tags.tr(ui.tags.td(k), ui.tags.td(v)) for k, v in rows.items()]
            )
