import pandas as pd
import pygwalker
pygwalker.GlobalVarManager.set_privacy("offline")
from pygwalker.api.anywidget import walk
from shiny import App, ui
from shinywidgets import output_widget, render_widget

df = pd.DataFrame({"a": range(100), "b": ["x", "y"] * 50})
app_ui = ui.page_fillable(ui.card(ui.card_header("pyg"), output_widget("w"), full_screen=True))

def server(input, output, session):
    @render_widget
    def w():
        return walk(df)

app = App(app_ui, server)
