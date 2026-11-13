from reactable import CellInfo, ColFormat, Column, Reactable
from reactable.data import cars_93
from shiny.express import ui
from shinywidgets import render_reactable

ui.page_opts(title="Formatting and conditional styling", fillable=True)

cars = cars_93.to_pandas()[["manufacturer", "model", "price", "mpg_city"]]


def mpg_style(info: CellInfo) -> dict[str, str]:
    if info.value >= 25:
        return {"color": "#1a7f37", "fontWeight": "600"}
    if info.value <= 18:
        return {"color": "#cf222e", "fontWeight": "600"}
    return {}


with ui.card(full_screen=True):

    @render_reactable
    def tbl():
        return Reactable(
            cars,
            columns={
                "price": Column(name="Price", format=ColFormat(prefix="$", digits=1)),
                "mpg_city": Column(name="MPG (city)", style=mpg_style),
            },
            highlight=True,
        )
