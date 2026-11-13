# title: Cars '93 dashboard
# description: A fuller reactable dashboard: a type filter and a grouping
#     toggle re-render the table; page size updates in place; row selection
#     drives a comparison card; the search box drives a small chart of what's
#     currently visible. Exercises selected_rows(), search(), an in-place prop
#     update, grouping/aggregation, a JS cell renderer, and theming together.
# bucket: showcase
# run: uv run --no-sync --with reactable shiny run docs/widget-guides/reactable/gallery/showcase_cars_dashboard.py
# data: reactable.data.cars_93 (ships with the reactable package)
#
# NOTE: this header uses comments, not a module docstring. In Shiny Express,
# top-level bare string literals (including a module docstring) are treated
# like a REPL result and get auto-displayed as page content.

import matplotlib.pyplot as plt
from reactable import JS, CellInfo, ColFormat, Column, Reactable, Theme
from reactable.data import cars_93
from shiny import reactive, req
from shiny.express import input, render, ui
from shinywidgets import render_reactable

ui.page_opts(title="Cars '93 dashboard", fillable=True)

cars = cars_93.to_pandas()[
    ["manufacturer", "model", "type", "price", "mpg_city", "horsepower"]
]
TYPES = ["All", *sorted(cars["type"].unique())]

with ui.sidebar():
    ui.input_select("type", "Vehicle type", choices=TYPES)
    ui.input_switch("grouped", "Group by manufacturer", value=False)
    ui.input_slider("page_size", "Rows per page", min=4, max=20, value=8)

mpg_bar = JS(
    "function(cellInfo) {"
    "  const pct = Math.round((cellInfo.value / 35) * 100);"
    "  return '<div style=\"background:#e8f0fe\"><div style=\"background:#1a73e8;"
    "color:white;padding:1px 4px;width:' + pct + '%\">' + cellInfo.value + '</div></div>';"
    "}"
)

# aggregate="mean" silently renders blank cells with a pandas DataFrame
# (reactable-py's pandas column-type detection always reports "UNKNOWN"
# instead of "numeric", and "mean" only runs for numeric-typed columns).
# A JS aggregate function sidesteps it.
mean_js = JS("values => values.reduce((a, b) => a + b, 0) / values.length")


def price_style(info: CellInfo) -> dict[str, str]:
    return {"fontWeight": "600"} if info.value >= 30 else {}


def visible_data():
    df = cars if input.type() == "All" else cars[cars["type"] == input.type()]
    return df


with ui.layout_columns(col_widths=[8, 4]):
    with ui.card(full_screen=True):
        ui.card_header("Cars")

        @render_reactable
        def tbl():
            df = visible_data()
            grouped = input.grouped()
            return Reactable(
                df,
                columns={
                    "price": Column(
                        name="Price",
                        format=ColFormat(prefix="$", digits=1),
                        style=None if grouped else price_style,
                        aggregate=mean_js if grouped else None,
                    ),
                    "mpg_city": Column(
                        name="MPG (city)",
                        cell=None if grouped else mpg_bar,
                        html=not grouped,
                        aggregate=mean_js if grouped else None,
                    ),
                    "model": Column(aggregate="count" if grouped else None),
                },
                group_by=["manufacturer"] if grouped else None,
                selection=None if grouped else "multiple",
                on_click=None if grouped else "select",
                searchable=True,
                filterable=not grouped,
                highlight=True,
                theme=Theme(striped_color="#f6f8fa"),
                striped=True,
            )

        @reactive.effect
        def _():
            w = tbl.widget
            if w is not None:
                w.props = {**w.props, "defaultPageSize": input.page_size()}

    with ui.card():
        ui.card_header("Selected cars")

        @render.ui
        def detail():
            rows = tbl.selected_rows()
            req(len(rows) > 0)
            picked = visible_data().iloc[rows]
            return ui.TagList(
                ui.p(f"{len(picked)} selected, avg ${picked['price'].mean():.1f}k"),
                *[ui.p(f"- {r.manufacturer} {r.model}") for r in picked.itertuples()],
            )

    with ui.card():
        ui.card_header("Visible rows, by type (search-driven)")

        @render.plot
        def chart():
            query = tbl.search().lower()
            df = visible_data()
            if query:
                hit = df.astype(str).apply(lambda c: c.str.lower().str.contains(query))
                df = df[hit.any(axis=1)]
            fig, ax = plt.subplots(figsize=(4, 3))
            df["type"].value_counts().plot.barh(ax=ax)
            ax.set_xlabel("rows")
            return fig
