import panel as pn
import plotly.express as px
from shiny.express import ui
from shinywidgets import render_panel

pn.extension("tabulator")

gapminder_2007 = px.data.gapminder().query("year == 2007")

ui.page_opts(title="Tabulator formatters", fillable=True)

with ui.card(full_screen=True):
    ui.card_header("Life expectancy by country, 2007")

    @render_panel
    def table():
        return pn.widgets.Tabulator(
            gapminder_2007[["country", "continent", "lifeExp", "gdpPercap"]],
            selectable=True,
            disabled=True,
            theme="bootstrap5",
            layout="fit_columns",
            sizing_mode="stretch_both",
            formatters={
                "lifeExp": {
                    "type": "progress",
                    "min": 40,
                    "max": 85,
                    "color": ["#d7301f", "#fdae61", "#a6d96a", "#1a9850"],
                },
                "gdpPercap": {"type": "money", "symbol": "$", "precision": 0},
            },
        )
