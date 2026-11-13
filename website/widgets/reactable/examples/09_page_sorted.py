from reactable import Reactable
from reactable.data import cars_93
from shiny.express import render, ui
from shinywidgets import render_reactable

ui.page_opts(title="page() and sorted()", fillable=True)

cars = cars_93.to_pandas()[["manufacturer", "model", "price", "mpg_city"]]

with ui.layout_columns(col_widths=[8, 4]):
    with ui.card(full_screen=True):

        @render_reactable
        def tbl():
            return Reactable(cars, sortable=True, default_page_size=10)

    with ui.card():
        ui.card_header("Where the user is")

        @render.code
        def state():
            page_1based = tbl.page() + 1
            return f"page {page_1based}\nsorted {tbl.sorted()}"
