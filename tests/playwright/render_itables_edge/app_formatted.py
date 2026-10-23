from __future__ import annotations

import pandas as pd
from itables import JavascriptCode
from itables.widget import ITable
from shiny import App, ui
from shinywidgets import output_widget, render_itables

df = pd.DataFrame({"item": ["a", "b"], "price": [1234.5, 6.25]})

app_ui = ui.page_fluid(ui.card(output_widget("formatted")))


def server(input, output, session):
    @render_itables
    def formatted():
        # Cell formatting recipe from the itables docs, which relies on the global `$`
        # carrying the DataTables plugin
        return ITable(
            df,
            columnDefs=[
                {
                    "targets": [1],
                    "render": JavascriptCode(
                        "$.fn.dataTable.render.number(',', '.', 2, '$')"
                    ),
                }
            ],
        )


app = App(app_ui, server)
