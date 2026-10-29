import mols2grid
import pandas as pd
from rdkit import Chem
from rdkit.Chem import Descriptors
from shiny import App, reactive, render, ui
from shinywidgets import output_widget, render_mols2grid


def load_molecules() -> pd.DataFrame:
    df = mols2grid.sdf_to_dataframe(mols2grid.datafiles.SOLUBILITY_SDF)
    df = df.rename(columns={"SOL": "LogS", "SOL_classification": "Class"})
    keep = [c for c in ("SMILES", "ID", "LogS", "Class") if c in df.columns]
    df = df[keep].reset_index(drop=True)
    # A few SMILES in this dataset can't be parsed by current RDKit, so guard
    mw = []
    for smiles in df["SMILES"]:
        mol = Chem.MolFromSmiles(smiles)
        mw.append(round(Descriptors.MolWt(mol), 1) if mol is not None else float("nan"))
    df["MW"] = mw
    return df.dropna(subset=["MW"]).reset_index(drop=True)


MOLS = load_molecules()

app_ui = ui.page_sidebar(
    ui.sidebar(
        ui.h5("Filter (Python -> browser)"),
        ui.input_slider(
            "mw",
            "Molecular weight",
            min=float(MOLS["MW"].min()),
            max=float(MOLS["MW"].max()),
            value=(float(MOLS["MW"].min()), float(MOLS["MW"].max())),
            step=5,
        ),
        ui.input_select(
            "cls",
            "Solubility class",
            choices=["All"] + sorted(MOLS["Class"].dropna().unique().tolist()),
        ),
        ui.hr(),
        ui.h5("Selection (browser -> Python)"),
        ui.output_text("n_selected"),
        ui.output_data_frame("selected"),
        width=340,
    ),
    ui.card(
        ui.card_header("Solubility dataset — click a molecule to select it"),
        output_widget("grid"),
        class_="border-0",
    ),
    title="mols2grid x Shiny for Python",
    fillable=True,
)


def server(input, output, session):
    @render_mols2grid(subset=["ID"], tooltip=["ID", "MW", "LogS", "Class"])
    def grid():
        return MOLS

    # Python -> browser: filtering reuses the grid already in the page
    @reactive.effect
    def _filter():
        grid_obj = grid.grid
        if grid_obj is None:
            return
        lo, hi = input.mw()
        mask = MOLS["MW"].between(lo, hi)
        if input.cls() != "All":
            mask &= MOLS["Class"] == input.cls()
        grid_obj.filter(mask.tolist())

    # browser -> Python: the selection is the rendered rows' positional
    # indices, so it can be located directly in the source DataFrame
    @reactive.calc
    def selected_rows() -> pd.DataFrame:
        return MOLS.loc[[int(k) for k in (grid.selection or {})]]

    @render.text
    def n_selected():
        return f"{len(selected_rows())} molecule(s) selected"

    @render.data_frame
    def selected():
        df = selected_rows()
        return render.DataGrid(df[["ID", "MW", "LogS"]], width="100%")


app = App(app_ui, server)
