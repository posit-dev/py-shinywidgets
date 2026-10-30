from __future__ import annotations

import pandas as pd
from reactable import ColFormat, Column, Reactable
from shiny import App, reactive, render, ui
from shinywidgets import output_widget, render_reactable

DATA = pd.DataFrame(
    {
        "name": ["alpha", "beta", "gamma", "delta", "epsilon", "zeta"],
        "value": [1.5, None, 3.25, 4.0, 5.5, 6.75],
        "group": ["a", "a", "b", "b", "c", "c"],
    }
)

app_ui = ui.page_fluid(
    ui.input_action_button("rerender", "Rerender"),
    ui.input_numeric("page_size", "Page size (in-place)", 4, min=1, max=10),
    ui.card(
        ui.card_header("Interactive"),
        output_widget("tbl"),
        id="tbl_card",
    ),
    ui.card(
        ui.card_header("Fixed height prop"),
        output_widget("fixed"),
        id="fixed_card",
    ),
    ui.card(
        ui.card_header("Selectable"),
        output_widget("sel"),
        id="sel_card",
    ),
    ui.card(
        ui.card_header("Table state (accessors)"),
        ui.output_text("tbl_state"),
        ui.output_text("sel_state"),
        id="state_card",
    ),
)


def server(input, output, session):
    @render_reactable
    def tbl():
        input.rerender()  # re-render dependency
        return Reactable(
            DATA,
            columns={
                "value": Column(name="Value", format=ColFormat(prefix="$", digits=2)),
            },
            filterable=True,
            searchable=True,
            default_page_size=4,
        )

    @render_reactable
    def fixed():
        return Reactable(DATA, height=250)

    @render_reactable
    def sel():
        return Reactable(DATA, selection="multiple", default_page_size=4)

    @render.text
    def tbl_state():
        return (
            f"page={tbl.page()} sorted={tbl.sorted()} "
            f"filtered={tbl.filtered()} search={tbl.search()}"
        )

    @render.text
    def sel_state():
        return f"selected={sel.selected_rows()}"

    @reactive.effect
    def _():
        # In-place (non-data) props update
        w = tbl.widget
        if w is not None:
            w.props = {**w.props, "defaultPageSize": input.page_size()}


app = App(app_ui, server)
