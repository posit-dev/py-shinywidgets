import panel as pn
import plotly.express as px
from shiny import reactive
from shiny.express import ui
from shinywidgets import render_panel

pn.extension("tabulator")

latest = px.data.gapminder().query("year == 2007").sort_values("pop", ascending=False).head(15)

ui.page_opts(title="Click a row to update a detail card in place", fillable=True)

with ui.layout_columns(col_widths=[7, 5]):
    with ui.card(full_screen=True):
        ui.card_header("Click a country")

        @render_panel
        def table():
            return pn.widgets.Tabulator(
                latest[["country", "continent", "lifeExp", "pop"]],
                selectable=1, disabled=True, theme="bootstrap5",
                layout="fit_columns", sizing_mode="stretch_both",
            )

    with ui.card():
        ui.card_header("Selected country (updated in place, not re-rendered)")

        @render_panel
        def detail():
            # Built once with a placeholder; the effect below mutates it.
            return pn.indicators.Number(
                name="Select a row", value=0, format="{value:.1f} yrs",
                sizing_mode="stretch_width",
            )


@reactive.effect
def _():
    idx = table.param("selection")
    ind = detail.value
    if not idx:
        ind.name, ind.value = "Select a row", 0
    else:
        row = table.value.value.iloc[idx[0]]
        ind.name = f"{row['country']} -- life expectancy"
        ind.value = row["lifeExp"]
