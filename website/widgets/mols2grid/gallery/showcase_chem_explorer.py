# Chemical explorer: sliders + lasso jointly filter a mols2grid grid, with a
# click-to-inspect detail card and a selection -> SDF download.
# Bucket: showcase.
# Run: shiny run docs/widget-guides/mols2grid/gallery/showcase_chem_explorer.py
# Data: mols2grid's bundled ESOL/Delaney solubility SDF (mols2grid.datafiles).

from __future__ import annotations

import io

import matplotlib.pyplot as plt
import mols2grid
import pandas as pd
import plotly.express as px
from rdkit import Chem
from rdkit.Chem import Descriptors, Draw
from shiny import reactive, render, req
from shiny.express import input, ui
from shinywidgets import render_mols2grid, render_plotly


def load_molecules() -> pd.DataFrame:
    df = mols2grid.sdf_to_dataframe(mols2grid.datafiles.SOLUBILITY_SDF)
    df = df[["SMILES", "ID", "SOL"]].rename(columns={"SOL": "LogS"}).reset_index(drop=True)
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

ui.page_opts(title="Chemical explorer", fillable=True)

with ui.sidebar():
    ui.input_slider("mw", "Molecular weight", min=mw_lo, max=mw_hi, value=(mw_lo, mw_hi))
    ui.input_slider("logp", "LogP", min=logp_lo, max=logp_hi, value=(logp_lo, logp_hi))
    ui.hr()
    ui.markdown(
        "Lasso- or box-select points in the scatter plot to narrow the grid "
        "further (combined with the sliders above). Click a molecule's image "
        "for its detail card; use the checkbox to add it to the selection."
    )

with ui.layout_columns(col_widths=[5, 4, 3]):
    with ui.card(full_screen=True):
        ui.card_header("Solubility dataset (257 molecules)")

        @render_mols2grid(
            clicks=True, subset=["ID"], tooltip=["ID", "MW", "LogP", "LogS"]
        )
        def grid():
            return MOLS

    with ui.card(full_screen=True):
        ui.card_header("MW vs. LogP (lasso to filter)")

        @render_plotly
        def scatter():
            fig = px.scatter(
                MOLS, x="MW", y="LogP", custom_data=[MOLS.index], opacity=0.6
            )
            fig.update_layout(dragmode="lasso", margin=dict(l=10, r=10, t=10, b=10))
            return fig

    with ui.layout_columns(col_widths=12):
        with ui.card():
            ui.card_header("Click a molecule")

            @render.plot
            def depiction():
                row = grid.clicked()
                req(row is not None)
                mol = Chem.MolFromSmiles(row["SMILES"])
                fig, ax = plt.subplots(figsize=(3, 2.2))
                ax.imshow(Draw.MolToImage(mol, size=(300, 220)))
                ax.axis("off")
                return fig

            @render.ui
            def descriptors():
                row = grid.clicked()
                if row is None:
                    return ui.p("Click a molecule's image to inspect it.")
                return ui.TagList(
                    ui.tags.b(row["ID"]),
                    ui.tags.br(),
                    f"MW {row['MW']}  LogP {row['LogP']}  LogS {row['LogS']}",
                )

        with ui.card():
            ui.card_header("Checkbox selection")

            @render.text
            def n_selected():
                return f"{len(grid.selected() or {})} molecule(s) selected"

            @render.download_button(
                filename="selected_molecules.sdf", label="Download as SDF"
            )
            def download():
                sel = grid.selected() or {}
                writer_out = io.StringIO()
                writer = Chem.SDWriter(writer_out)
                for idx in sel:
                    row = MOLS.loc[int(idx)]
                    mol = Chem.MolFromSmiles(row["SMILES"])
                    if mol is not None:
                        mol.SetProp("_Name", str(row["ID"]))
                        writer.write(mol)
                writer.close()
                yield writer_out.getvalue()


@reactive.calc
def slider_mask() -> pd.Series:
    lo, hi = input.mw()
    plo, phi = input.logp()
    return MOLS["MW"].between(lo, hi) & MOLS["LogP"].between(plo, phi)


@reactive.calc
def lasso_mask() -> pd.Series:
    if scatter.selected() is None:
        return pd.Series(True, index=MOLS.index)
    selected = scatter.selected_rows(MOLS)
    return pd.Series(MOLS.index.isin(selected.index), index=MOLS.index)


@reactive.effect
def _filter_grid():
    # In-place filter(): sliders and the lasso both narrow the same grid
    # without ever re-rendering it, so checkbox selections and scroll
    # position survive every adjustment.
    if grid.grid is None:
        return
    mask = slider_mask() & lasso_mask()
    grid.grid.filter(mask.tolist())
