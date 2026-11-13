import io

from reactable import ColFormat, Column, Reactable
from reactable.data import cars_93
from shiny.express import render, ui
from shinywidgets import render_reactable

ui.page_opts(title="Read on demand: export selected rows", fillable=True)

cars = cars_93.to_pandas()[["manufacturer", "model", "price", "mpg_city"]]

with ui.layout_columns(col_widths=[8, 4]):
    with ui.card(full_screen=True):

        @render_reactable
        def tbl():
            return Reactable(
                cars,
                selection="multiple",
                columns={"price": Column(format=ColFormat(prefix="$", digits=1))},
                default_page_size=8,
            )

    with ui.card():
        ui.card_header("Export")
        ui.p("Check some rows, then download -- no need to read selected_rows() anywhere else first.")

        # selected_rows() is live from the moment the table renders, whether
        # or not anything has read it yet, so this handler can read it cold,
        # the instant the user clicks download: no warm-up reader required.
        @render.download_button(filename="selected_cars.csv", label="Download selected as CSV")
        def download_csv():
            rows = tbl.selected_rows()
            buf = io.StringIO()
            cars.iloc[rows].to_csv(buf, index=False)
            yield buf.getvalue()
