from reactable import JS, Column, Reactable
from reactable.data import cars_93
from shiny.express import ui
from shinywidgets import render_reactable

ui.page_opts(title="Custom JS cell renderer", fillable=True)

cars = cars_93.to_pandas()[["manufacturer", "model", "mpg_city"]].head(12)

bar_cell = JS(
    "function(cellInfo) {"
    "  const pct = Math.round((cellInfo.value / 35) * 100);"
    "  return ("
    "    '<div style=\"background:#e8f0fe;border-radius:3px\">' +"
    "    '<div style=\"background:#1a73e8;color:white;padding:2px 6px;'"
    "    + 'border-radius:3px;width:' + pct + '%;white-space:nowrap\">' +"
    "    cellInfo.value + '</div></div>'"
    "  );"
    "}"
)

with ui.card(full_screen=True):

    @render_reactable
    def tbl():
        return Reactable(
            cars,
            columns={"mpg_city": Column(name="MPG (city)", cell=bar_cell, html=True)},
            pagination=False,
        )
