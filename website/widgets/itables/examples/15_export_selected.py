import io

import plotly.express as px
from itables.widget import ITable
from shiny.express import render, ui
from shinywidgets import render_itables

ui.page_opts(title="Read on demand: export selected rows", fillable=True)

countries = px.data.gapminder().query("year == 2007")[
    ["country", "continent", "lifeExp", "pop", "gdpPercap"]
].reset_index(drop=True)

with ui.layout_columns(col_widths=[8, 4]):
    with ui.card(full_screen=True):

        @render_itables
        def table():
            return ITable(countries, select=True)

    with ui.card():
        ui.card_header("Export")
        ui.p("Click some rows, then download -- no need to read selected_rows() anywhere else first.")

        # selected_rows() is live from the moment the table renders, whether
        # or not anything has read it yet, so this handler can read it cold,
        # the instant the user clicks download: no warm-up reader required.
        @render.download_button(filename="selected_countries.csv", label="Download selected as CSV")
        def download_csv():
            rows = table.selected_rows()
            buf = io.StringIO()
            countries.iloc[rows].to_csv(buf, index=False)
            yield buf.getvalue()
