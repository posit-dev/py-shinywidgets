# title: Filterable table with a selection summary
# description: A searchable, filterable reactable table whose selection drives
#     a small summary card -- a clean starting point for "pick some rows, see
#     a number" dashboards.
# bucket: template
# run: uv run --no-sync --with reactable shiny run docs/widget-guides/reactable/gallery/template_filterable_table.py
# data: reactable.data.cars_93 (ships with the reactable package)
#
# NOTE: this header uses comments, not a module docstring. In Shiny Express,
# top-level bare string literals (including a module docstring) are treated
# like a REPL result and get auto-displayed as page content.

from reactable import ColFormat, Column, Reactable
from reactable.data import cars_93
from shiny import req
from shiny.express import render, ui
from shinywidgets import render_reactable

ui.page_opts(title="Cars '93 explorer", fillable=True)

cars = cars_93.to_pandas()[
    ["manufacturer", "model", "type", "price", "mpg_city", "horsepower"]
]

with ui.layout_columns(col_widths=[8, 4]):
    with ui.card(full_screen=True):
        ui.card_header("Cars (search, filter, select)")

        @render_reactable
        def tbl():
            return Reactable(
                cars,
                columns={
                    "price": Column(
                        name="Price", format=ColFormat(prefix="$", digits=1)
                    ),
                    "mpg_city": Column(name="MPG (city)"),
                },
                selection="multiple",
                searchable=True,
                filterable=True,
                highlight=True,
                default_page_size=8,
            )

    with ui.card():
        ui.card_header("Selection summary")

        @render.ui
        def summary():
            rows = tbl.selected_rows()
            req(len(rows) > 0)
            picked = cars.iloc[rows]
            return ui.TagList(
                ui.p(f"{len(picked)} car(s) selected"),
                ui.p(f"Avg. price: ${picked['price'].mean():.1f}k"),
                ui.p(f"Avg. MPG (city): {picked['mpg_city'].mean():.1f}"),
            )
