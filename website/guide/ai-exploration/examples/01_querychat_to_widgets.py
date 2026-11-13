# Ask querychat to filter the data in plain English; the same filtered
# frame drives a plotly scatter plot (updated IN PLACE, so zoom/pan survive)
# and an itables table (re-rendered -- a table has no camera state worth
# preserving). Try: "just the countries in the Americas with gdp per capita
# over 20000".
import chatlas
import plotly.graph_objects as go
import plotly.express as px
from shiny import reactive
from shiny.express import ui
from querychat.express import QueryChat

from shinywidgets import render_itables, render_plotly

gapminder = px.data.gapminder().query("year == 2007").reset_index(drop=True)

qc = QueryChat(
    gapminder,
    "gapminder",
    client=chatlas.ChatAnthropic(model="claude-haiku-5-5"),
    tools=("filter", "query"),  # skip querychat's own chart tool; we have our own
    greeting="Ask me to filter the 2007 gapminder countries, e.g. "
    "\"just the Americas with gdp per capita over 20000\".",
)

ui.page_opts(title="querychat drives a chart and a table", fillable=True)

with ui.sidebar(width=380):
    qc.ui()

with ui.layout_columns(col_widths=[7, 5]):
    with ui.card(full_screen=True):
        ui.card_header("All countries; querychat's matches lit up")

        @render_plotly
        def scatter():
            return go.FigureWidget(
                go.Scatter(
                    x=gapminder["gdpPercap"],
                    y=gapminder["lifeExp"],
                    mode="markers",
                    marker={"color": "#ccc", "size": 8},
                    text=gapminder["country"],
                )
            ).update_xaxes(type="log", title="GDP per capita").update_yaxes(
                title="Life expectancy"
            )

        @reactive.effect
        def _highlight_matches():
            matched = set(qc.df()["country"])
            all_matched = len(matched) == len(gapminder)  # no filter applied yet
            with reactive.isolate():
                scatter.widget.data[0].marker.color = [
                    "#ccc" if all_matched or c not in matched else "#e41a1c"
                    for c in gapminder["country"]
                ]

    with ui.card(full_screen=True):
        ui.card_header("querychat's current result set")

        @render_itables
        def table():
            cols = ["country", "continent", "lifeExp", "gdpPercap", "pop"]
            return qc.df()[cols]
