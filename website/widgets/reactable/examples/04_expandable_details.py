from reactable import Column, Reactable, RowInfo
from reactable.data import cars_93
from shiny.express import ui
from shinywidgets import render_reactable

ui.page_opts(title="Expandable row details", fillable=True)

cars = cars_93.to_pandas()[
    ["manufacturer", "model", "price", "horsepower", "passengers", "origin"]
]


def row_detail(row: RowInfo) -> str:
    car = cars.iloc[row.row_index]
    return (
        "<div style='padding:8px 16px'>"
        f"<b>{car.manufacturer} {car.model}</b> &mdash; "
        f"{car.horsepower} hp, seats {car.passengers}, built in {car.origin}."
        "</div>"
    )


with ui.card(full_screen=True):

    @render_reactable
    def tbl():
        return Reactable(
            cars[["manufacturer", "model", "price"]],
            # The details column needs its own `html=True` to render markup
            # instead of escaping it as text.
            details=Column(details=row_detail, html=True),
            highlight=True,
        )
