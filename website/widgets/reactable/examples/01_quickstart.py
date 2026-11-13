from reactable import ColFormat, Column, Reactable
from reactable.data import cars_93
from shiny.express import ui
from shinywidgets import render_reactable

ui.page_opts(title="reactable + shinywidgets", fillable=True)

cars = cars_93.to_pandas()[["manufacturer", "model", "type", "price", "mpg_city"]]

with ui.card(full_screen=True):

    @render_reactable
    def tbl():
        return Reactable(
            cars,
            columns={"price": Column(format=ColFormat(prefix="$", digits=1))},
            searchable=True,
            filterable=True,
            highlight=True,
            striped=True,
        )
