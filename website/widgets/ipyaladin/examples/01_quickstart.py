from ipyaladin import Aladin
from shiny.express import ui
from shinywidgets import render_ipyaladin

ui.page_opts(title="ipyaladin quick start", fillable=True)

with ui.card(full_screen=True):
    ui.card_header("Orion Nebula (M42)")

    @render_ipyaladin
    def sky():
        return Aladin(target=(83.82, -5.39), fov=1.2)
