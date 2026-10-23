from __future__ import annotations

import pandas as pd
from itables.widget import ITable
from shiny import App, ui
from shinywidgets import output_widget, render_itables

df = pd.DataFrame({"n": range(5)})

app_ui = ui.page_fluid(
    # End state of a classic page script that ran `var $` before jQuery loaded:
    # the global binding is writable but non-configurable (so no accessor can be
    # installed on it), holding the page jQuery
    ui.tags.script(
        "Object.defineProperty(window, '$', "
        "{ value: window.jQuery, writable: true, configurable: false });"
    ),
    output_widget("table"),
)


def server(input, output, session):
    @render_itables
    def table():
        return ITable(df)


app = App(app_ui, server)
