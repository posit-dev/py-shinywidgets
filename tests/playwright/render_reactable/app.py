from __future__ import annotations

import pandas as pd
from reactable import ColFormat, Column, Reactable
from shiny import App, reactive, ui
from shinywidgets import output_widget, render_reactable

DATA = pd.DataFrame(
    {
        "name": ["alpha", "beta", "gamma", "delta", "epsilon", "zeta"],
        "value": [1.5, None, 3.25, 4.0, 5.5, 6.75],
        "group": ["a", "a", "b", "b", "c", "c"],
    }
)

app_ui = ui.page_fillable(
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
            default_page_size=4,
        )

    @render_reactable
    def fixed():
        return Reactable(DATA, height=250)

    @reactive.effect
    def _():
        # In-place (non-data) props update
        w = tbl.widget
        if w is not None:
            w.props = {**w.props, "defaultPageSize": input.page_size()}


app = App(app_ui, server)
