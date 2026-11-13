from reactable import ColFormat, ColGroup, Column, Reactable
from reactable.data import cars_93
from shiny.express import ui
from shinywidgets import render_reactable

ui.page_opts(title="Column groups and footers", fillable=True)

cars = cars_93.to_pandas()[
    ["manufacturer", "model", "min_price", "price", "max_price", "mpg_city"]
]


def avg_footer(info) -> str:
    return f"${sum(info.values) / len(info.values):.1f}"


with ui.card(full_screen=True):

    @render_reactable
    def tbl():
        return Reactable(
            cars,
            columns={
                "min_price": Column(name="Min", format=ColFormat(prefix="$", digits=1)),
                "price": Column(
                    name="Avg",
                    format=ColFormat(prefix="$", digits=1),
                    footer=avg_footer,
                ),
                "max_price": Column(name="Max", format=ColFormat(prefix="$", digits=1)),
            },
            column_groups=[ColGroup(name="Price ($1000s)", columns=["min_price", "price", "max_price"])],
            pagination=False,
        )
