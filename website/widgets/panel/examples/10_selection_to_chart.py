import panel as pn
import plotly.express as px
from shiny.express import ui
from shinywidgets import render_panel, render_plotly

pn.extension("tabulator")

gapminder = px.data.gapminder()
latest = gapminder[gapminder["year"] == 2007].sort_values("pop", ascending=False).head(15)

ui.page_opts(title="Table selection drives a plotly chart", fillable=True)

with ui.layout_columns(col_widths=[7, 5]):
    with ui.card(full_screen=True):
        ui.card_header("The 15 most populous countries, 2007 (select some rows)")

        @render_panel
        def table():
            return pn.widgets.Tabulator(
                latest[["country", "continent", "pop"]],
                selectable=True, disabled=True, theme="bootstrap5",
                layout="fit_columns", sizing_mode="stretch_both",
            )

    with ui.card(full_screen=True):
        ui.card_header("Life expectancy trend of the selected countries")

        @render_plotly
        def trend():
            idx = table.param("selection")
            countries = table.value.value.iloc[idx]["country"].tolist() if idx else []
            df = gapminder[gapminder["country"].isin(countries)] if countries else gapminder.iloc[:0]
            return px.line(df, x="year", y="lifeExp", color="country", markers=True)
