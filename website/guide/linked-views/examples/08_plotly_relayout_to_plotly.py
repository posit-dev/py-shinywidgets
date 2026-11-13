import plotly.express as px
from shiny.express import ui
from shinywidgets import render_plotly

df = px.data.gapminder().query("year == 2007").reset_index(drop=True)

ui.page_opts(title="Zoom to filter a second view", fillable=True)

with ui.layout_columns(col_widths=[7, 5]):
    with ui.card(full_screen=True):

        @render_plotly
        def scatter():
            return px.scatter(df, x="lifeExp", y="gdpPercap", color="continent")

    with ui.card(full_screen=True):
        ui.card_header("Mean GDP/capita in the visible life-expectancy range")

        @render_plotly
        def summary_bar():
            axes = scatter.relayout() or {}
            if "xaxis.range[0]" in axes:
                lo, hi = axes["xaxis.range[0]"], axes["xaxis.range[1]"]
                visible = df[df["lifeExp"].between(lo, hi)]
            else:
                visible = df
            means = visible.groupby("continent", as_index=False)["gdpPercap"].mean()
            return px.bar(means, x="continent", y="gdpPercap")
