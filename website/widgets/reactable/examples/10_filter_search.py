from reactable import Reactable
from reactable.data import cars_93
from shiny.express import render, ui
from shinywidgets import render_reactable

ui.page_opts(title="filtered() and search()", fillable=True)

cars = cars_93.to_pandas()[["manufacturer", "model", "type", "price"]]

with ui.layout_columns(col_widths=[8, 4]):
    with ui.card(full_screen=True):

        @render_reactable
        def tbl():
            return Reactable(cars, filterable=True, searchable=True, default_page_size=8)

    with ui.card():
        ui.card_header("What's visible (debounced 250ms)")

        @render.code
        def state():
            return f"filtered {tbl.filtered()}\nsearch {tbl.search()!r}"
