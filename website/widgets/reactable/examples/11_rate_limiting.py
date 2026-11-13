from reactable import Reactable
from reactable.data import cars_93
from shiny.express import render, ui
from shinywidgets import render_reactable

ui.page_opts(title="Rate limiting", fillable=True)

cars = cars_93.to_pandas()[["manufacturer", "model", "type", "price"]]

with ui.layout_columns(col_widths=[8, 4]):
    with ui.card(full_screen=True):
        # A longer debounce (1s) than the 250ms default: useful if reading
        # search()/filtered() triggers expensive downstream work (a database
        # query, a heavy re-plot) you don't want firing on every keystroke.
        @render_reactable(rate_policy="debounce", rate_delay=1.0)
        def tbl():
            return Reactable(cars, searchable=True, default_page_size=8)

    with ui.card():
        ui.card_header("search() (1s debounce)")

        @render.code
        def state():
            return repr(tbl.search())
