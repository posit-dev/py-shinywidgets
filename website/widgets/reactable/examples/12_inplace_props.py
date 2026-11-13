from reactable import Reactable
from reactable.data import cars_93
from shiny import reactive
from shiny.express import input, ui
from shinywidgets import render_reactable

ui.page_opts(title="In-place prop update", fillable=True)

cars = cars_93.to_pandas()[["manufacturer", "model", "price"]]

ui.input_slider("page_size", "Rows per page", min=3, max=20, value=6)

with ui.card(full_screen=True):

    @render_reactable
    def tbl():
        return Reactable(cars, default_page_size=6)

    @reactive.effect
    def _():
        # A non-data prop updates the mounted widget directly: no re-render,
        # no re-sent JS bundle, and any sort/filter/selection stays intact.
        w = tbl.widget
        if w is not None:
            w.props = {**w.props, "defaultPageSize": input.page_size()}
