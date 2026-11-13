from ipyaladin import Aladin
from shiny.express import ui
from shinywidgets import render_ipyaladin

ui.page_opts(title="Fill vs. fixed height", fillable=True)

with ui.layout_columns():
    with ui.card(full_screen=True):
        ui.card_header("Fills the card")

        @render_ipyaladin
        def fills():
            return Aladin(target=(83.822, -5.391), fov=2)  # M42

    with ui.card():
        ui.card_header("Fixed height (Aladin(height=250))")

        @render_ipyaladin
        def fixed():
            return Aladin(target=(83.822, -5.391), fov=2, height=250)
