from reactable import ColFormat, Column, Reactable, Theme
from reactable.data import cars_93
from shiny.express import ui
from shinywidgets import render_reactable

ui.page_opts(title="Theming", fillable=True)

cars = cars_93.to_pandas()[["manufacturer", "model", "price", "mpg_city"]]

theme = Theme(
    color="#1b1f23",
    background_color="#ffffff",
    border_color="#d0d7de",
    striped_color="#f6f8fa",
    highlight_color="#eef3ff",
    header_style={"background": "#24292f", "color": "white"},
)

with ui.card(full_screen=True):

    @render_reactable
    def tbl():
        return Reactable(
            cars,
            columns={"price": Column(format=ColFormat(prefix="$", digits=1))},
            theme=theme,
            striped=True,
            highlight=True,
            bordered=True,
        )
