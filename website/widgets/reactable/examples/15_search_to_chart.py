import matplotlib.pyplot as plt
from reactable import Reactable
from reactable.data import cars_93
from shiny.express import render, ui
from shinywidgets import render_reactable

ui.page_opts(title="search() drives a chart", fillable=True)

cars = cars_93.to_pandas()[["manufacturer", "model", "type", "price"]]


def visible_rows():
    # search()/filtered() report the *query*, not the matching rows, so
    # showing "what's visible" elsewhere means reproducing reactable's
    # search (case-insensitive substring, any column) in pandas.
    query = tbl.search().lower()
    if not query:
        return cars
    hit = cars.astype(str).apply(lambda col: col.str.lower().str.contains(query))
    return cars[hit.any(axis=1)]


with ui.layout_columns(col_widths=[7, 5]):
    with ui.card(full_screen=True):

        @render_reactable
        def tbl():
            return Reactable(cars, searchable=True, default_page_size=8)

    with ui.card():
        ui.card_header("Visible rows, by type")

        @render.plot
        def chart():
            counts = visible_rows()["type"].value_counts()
            fig, ax = plt.subplots()
            counts.plot.barh(ax=ax)
            ax.set_xlabel("rows")
            return fig
