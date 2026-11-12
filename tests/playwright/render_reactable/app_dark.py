from __future__ import annotations

import pandas as pd
from reactable import Reactable
from shiny import App, ui
from shinywidgets import output_widget, render_reactable

app_ui = ui.page_fluid(
    ui.input_dark_mode(mode="dark"),
    output_widget("tbl"),
)


def server(input, output, session):
    @render_reactable
    def tbl():
        return Reactable(
            pd.DataFrame({"a": range(20), "b": range(100, 120)}),
            striped=True,
        )


app = App(app_ui, server)
