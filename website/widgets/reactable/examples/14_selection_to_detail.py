from reactable import ColFormat, Column, Reactable
from reactable.data import cars_93
from shiny import req
from shiny.express import render, ui
from shinywidgets import render_reactable

ui.page_opts(title="Selection drives a detail card", fillable=True)

cars = cars_93.to_pandas()[
    ["manufacturer", "model", "price", "horsepower", "mpg_city", "passengers"]
]

with ui.layout_columns(col_widths=[8, 4]):
    with ui.card(full_screen=True):

        @render_reactable
        def tbl():
            return Reactable(
                cars,
                selection="single",
                on_click="select",
                columns={"price": Column(format=ColFormat(prefix="$", digits=1))},
                default_page_size=8,
            )

    with ui.card():
        ui.card_header("Selected car")

        @render.ui
        def detail():
            rows = tbl.selected_rows()
            req(len(rows) > 0)
            car = cars.iloc[rows[0]]
            return ui.TagList(
                ui.h5(f"{car.manufacturer} {car.model}"),
                ui.p(f"${car.price}k, {car.horsepower} hp, {car.mpg_city} mpg city"),
                ui.p(f"Seats {car.passengers}"),
            )
