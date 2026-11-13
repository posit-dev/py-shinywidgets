from reactable import JS, ColFormat, Column, Reactable
from reactable.data import cars_93
from shiny.express import ui
from shinywidgets import render_reactable

ui.page_opts(title="Grouping and aggregation", fillable=True)

cars = cars_93.to_pandas()[["manufacturer", "model", "type", "price", "mpg_city"]]

# aggregate="mean" (and "sum"/"median") silently renders blank cells with a
# pandas DataFrame -- reactable-py's pandas column-type detection always
# reports "UNKNOWN" instead of "numeric", and those three aggregators only
# run for numeric-typed columns. A JS aggregate function sidesteps it.
mean_js = JS("values => values.reduce((a, b) => a + b, 0) / values.length")

with ui.card(full_screen=True):

    @render_reactable
    def tbl():
        return Reactable(
            cars,
            columns={
                "price": Column(
                    name="Avg. price",
                    aggregate=mean_js,
                    format=ColFormat(prefix="$", digits=1),
                ),
                "mpg_city": Column(name="Avg. MPG", aggregate=mean_js, format=ColFormat(digits=1)),
                "model": Column(name="# models", aggregate="count"),
            },
            group_by=["manufacturer"],
            default_expanded=False,
        )
