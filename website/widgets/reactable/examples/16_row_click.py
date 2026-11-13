from reactable import JS, Reactable
from reactable.data import cars_93
from shiny import req
from shiny.express import input, render, ui
from shinywidgets import render_reactable

ui.page_opts(title="Row clicks via on_click", fillable=True)

cars = cars_93.to_pandas()[["manufacturer", "model", "price"]]

# Clicks aren't part of reactable's reported state, so no accessor sees them.
# reactable's own `on_click=JS(...)` prop can forward a click as an ordinary
# Shiny input instead.
on_click = JS(
    "function(rowInfo, colInfo) {"
    "  Shiny.setInputValue('row_clicked', "
    "    {row: rowInfo.index, col: colInfo.id}, {priority: 'event'});"
    "}"
)

with ui.layout_columns(col_widths=[8, 4]):
    with ui.card(full_screen=True):

        @render_reactable
        def tbl():
            return Reactable(cars, on_click=on_click, default_page_size=8)

    with ui.card():
        ui.card_header("input.row_clicked()")

        @render.code
        def clicked():
            req(input.row_clicked())
            return str(input.row_clicked())
