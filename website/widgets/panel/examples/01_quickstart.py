import panel as pn
import plotly.express as px
from shiny.express import ui
from shinywidgets import render_panel

pn.extension("tabulator")

tips = px.data.tips()

ui.page_opts(title="Panel quickstart", fillable=True)

with ui.card(full_screen=True):
    ui.card_header("A Panel Tabulator, with no Panel server")

    @render_panel
    def table():
        return pn.widgets.Tabulator(
            tips,
            selectable=True,
            disabled=True,
            theme="bootstrap5",
            layout="fit_columns",
            sizing_mode="stretch_both",
        )
