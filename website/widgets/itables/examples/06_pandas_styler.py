from __future__ import annotations

import plotly.express as px
from itables.widget import ITable
from shiny.express import ui
from shinywidgets import render_itables

countries = px.data.gapminder().query("year == 2007")[
    ["country", "continent", "lifeExp", "pop", "gdpPercap"]
].reset_index(drop=True)

ui.page_opts(title="pandas Styler", fillable=True)

with ui.card(full_screen=True):
    ui.card_header("A pandas Styler's gradient and number format, rendered as-is")

    @render_itables
    def table():
        styler = (
            countries.style.background_gradient(subset=["lifeExp"], cmap="RdYlGn")
            .format({"lifeExp": "{:.1f}", "gdpPercap": "${:,.0f}", "pop": "{:,.0f}"})
        )
        # A Styler always carries HTML (its inline styles), so itables requires
        # an explicit opt-in to render it.
        return ITable(styler, allow_html=True, select=True)
