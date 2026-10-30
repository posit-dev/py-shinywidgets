from __future__ import annotations

from reactable import ColFormat, Column, Reactable, Theme
from reactable.data import cars_93
from shiny import reactive
from shiny.express import input, ui
from shinywidgets import render_reactable

ui.page_opts(title="reactable + shinywidgets", fillable=True)

with ui.sidebar():
    ui.input_select(
        "type",
        "Vehicle type",
        choices=["All", "Compact", "Midsize", "Small", "Sporty", "Van", "Large"],
    )
    ui.input_switch("group", "Group by manufacturer", value=False)
    ui.input_numeric("page_size", "Rows per page", 8, min=3, max=25)

COLS = ["manufacturer", "model", "type", "price", "mpg_city"]


def filter_data():
    df = cars_93[:, COLS]
    if input.type() != "All":
        idx = [i for i, t in enumerate(df["type"]) if t == input.type()]
        df = df[idx, :]
    return df


with ui.card(full_screen=True):
    ui.card_header("Cars '93 (sort, filter, and search in the table)")

    @render_reactable
    def tbl():
        grouped = input.group()
        return Reactable(
            filter_data(),
            columns={
                "price": Column(
                    name="Price",
                    format=ColFormat(prefix="$", digits=2),
                    aggregate="max" if grouped else None,
                ),
                "mpg_city": Column(
                    name="MPG (city)",
                    aggregate="mean" if grouped else None,
                    format=ColFormat(digits=1),
                ),
                "model": Column(aggregate="count" if grouped else None),
            },
            group_by=["manufacturer"] if grouped else None,
            filterable=True,
            searchable=True,
            highlight=True,
            striped=True,
            compact=True,
            theme=Theme(striped_color="#f6f8fa"),
        )

    @reactive.effect
    def _():
        # Page size updates in place (no re-render); data changes re-render
        w = tbl.widget
        if w is not None:
            w.props = {**w.props, "defaultPageSize": input.page_size()}
