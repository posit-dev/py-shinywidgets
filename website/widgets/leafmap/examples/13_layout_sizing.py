import leafmap
from shiny.express import ui
from shinywidgets import render_leafmap

ui.page_opts(title="leafmap layout and sizing", fillable=True)

with ui.layout_columns(col_widths=(6, 6)):
    with ui.card(full_screen=True):
        ui.card_header("Default: fills the card")

        @render_leafmap
        def fills():
            # leafmap.Map() defaults to a 600px Layout.height; render_leafmap
            # treats that default as unset and fills the card instead
            return leafmap.Map(center=(47.6, -122.33), zoom=10)

    with ui.card():
        ui.card_header('render_leafmap(height="220px")')

        @render_leafmap(height="220px")
        def fixed():
            return leafmap.Map(center=(47.6, -122.33), zoom=10)
