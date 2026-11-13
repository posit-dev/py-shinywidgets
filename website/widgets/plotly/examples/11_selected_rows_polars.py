import plotly.express as px
import polars as pl
from shiny.express import render, ui
from shinywidgets import render_plotly

pdf = px.data.gapminder().query("year == 2007")
df = pl.from_pandas(pdf[["country", "continent", "gdpPercap", "lifeExp"]])

ui.page_opts(title="Lasso-select countries (polars)", fillable=True)

with ui.layout_columns(col_widths=[7, 5]):
    with ui.card(full_screen=True):

        @render_plotly
        def plot():
            fig = px.scatter(
                df,
                x="gdpPercap",
                y="lifeExp",
                color="continent",
                log_x=True,
                custom_data=["country"],
            )
            fig.update_layout(dragmode="lasso")
            return fig

    with ui.card(full_screen=True):
        ui.card_header("plot.selected_rows(df, key='country')")

        @render.data_frame
        def rows():
            rows = plot.selected_rows(df, key="country")
            rows = rows.with_columns(pl.col("gdpPercap", "lifeExp").round(1))
            return render.DataGrid(rows.to_pandas())
