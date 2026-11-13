from reactable import Reactable
from reactable.data import cars_93
from shiny.express import render, ui
from shinywidgets import render_reactable

ui.page_opts(title="selected_rows()", fillable=True)

cars = cars_93.to_pandas()[["manufacturer", "model", "price"]].head(8)

with ui.layout_columns(col_widths=[8, 4]):
    with ui.card(full_screen=True):

        @render_reactable
        def tbl():
            return Reactable(cars, selection="multiple", default_page_size=8)

    with ui.card():
        ui.card_header("tbl.selected_rows()")

        @render.code
        def selected():
            return str(tbl.selected_rows())
