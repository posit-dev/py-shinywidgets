import pandas as pd
import panel as pn
import plotly.express as px
from shiny import reactive
from shiny.express import input, ui
from shinywidgets import render_panel

pn.extension("tabulator")

gapminder = px.data.gapminder()
years = sorted(gapminder["year"].unique().tolist())

ui.page_opts(title="Updating a Panel table in place", fillable=True)

with ui.card(full_screen=True):
    ui.input_slider("year", "Year", min=years[0], max=years[-1], value=years[0], step=5)

    @render_panel
    def table():
        with reactive.isolate():
            df = gapminder[gapminder["year"] == input.year()]
        return pn.widgets.Tabulator(
            df[["country", "continent", "lifeExp", "pop"]],
            selectable=True, disabled=True, theme="bootstrap5",
            layout="fit_columns", sizing_mode="stretch_both",
        )


@reactive.effect
def _():
    # Mutating `.value` in place (instead of returning a new Tabulator from
    # the render function) keeps the table's current client-side sort, and
    # re-points the row selection at the same countries by name.
    tab = table.value
    kept = set(tab.value.iloc[tab.selection]["country"])
    df = gapminder[gapminder["year"] == input.year()][
        ["country", "continent", "lifeExp", "pop"]
    ]
    tab.value = df
    tab.selection = [i for i, c in enumerate(df["country"]) if c in kept]
