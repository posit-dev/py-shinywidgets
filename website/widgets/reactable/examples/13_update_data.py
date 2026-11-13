import random

from reactable import ColFormat, Column, Reactable
from reactable.data import cars_93
from shiny import reactive
from shiny.express import input, ui
from shinywidgets import render_reactable

ui.page_opts(title="Updating data", fillable=True)

cars = cars_93.to_pandas()[["manufacturer", "model", "price"]].head(10)

ui.input_action_button("rerender", "Re-render (new widget, view resets)")
ui.input_action_button("inplace", "Update in place (view is preserved)")

with ui.card(full_screen=True):

    @render_reactable
    def tbl():
        input.rerender()
        prices = cars["price"] * random.uniform(0.8, 1.2)
        return Reactable(
            cars.assign(price=prices),
            columns={"price": Column(format=ColFormat(prefix="$", digits=1))},
            sortable=True,
        )

    @reactive.effect
    @reactive.event(input.inplace)
    def _():
        w = tbl.widget
        if w is None:
            return
        prices = [round(p, 1) for p in cars["price"] * random.uniform(0.8, 1.2)]
        # Reassigning `props["data"]` (not mutating the dict in place)
        # refreshes the table and keeps the current sort, filters, page, and
        # selection as the user left them.
        w.props = {**w.props, "data": {**w.props["data"], "price": prices}}
