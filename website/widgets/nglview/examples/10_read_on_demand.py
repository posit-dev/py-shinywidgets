import nglview
import pandas as pd
from shiny import reactive
from shiny.express import input, render, ui
from shinywidgets import render_nglview

ui.page_opts(fillable=True)

log = reactive.value(pd.DataFrame(columns=["resname", "resno", "chain"]))

with ui.layout_columns(col_widths=[7, 5]):
    with ui.card(full_screen=True):
        ui.card_header("Click an atom, then log it")

        @render_nglview
        def structure():
            view = nglview.show_file(
                nglview.datafiles.PDB, default_representation=False
            )
            view.add_representation("cartoon", color="lightgrey")
            view.add_representation("ball+stick", selection="hetero")
            view.center()
            return view

        ui.input_action_button("log", "Log current pick")

    with ui.card():
        ui.card_header("Logged residues")

        @render.data_frame
        def logged():
            return log.get()


# `picked` is live from the moment the viewer renders -- reading it here, in
# a button handler that may fire minutes after the last click, needs no
# warm-up read and never misses an interaction that happened before this
# ran.
@reactive.effect
@reactive.event(input.log)
def _log_pick():
    picked = structure.read("picked")
    atom = picked.get("atom1") if picked else None
    if atom is None:
        return
    row = {"resname": atom["resname"], "resno": atom["resno"], "chain": atom["chainname"]}
    with reactive.isolate():
        log.set(pd.concat([log.get(), pd.DataFrame([row])], ignore_index=True))
