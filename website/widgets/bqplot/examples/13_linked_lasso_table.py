# Pattern: lasso select -> filtered table. selected_rows() maps the lasso
# back to rows of the data frame, no manual event wiring.
import bqplot
import bqplot.interacts as interacts
import plotly.express as px
from shiny.express import render, ui
from shinywidgets import render_bqplot

ui.page_opts(title="Lasso to table", fillable=True)

gap2007 = px.data.gapminder().query("year == 2007").reset_index(drop=True)

with ui.layout_columns(col_widths=[7, 5]):
    with ui.card(full_screen=True):
        ui.card_header("Lasso countries")

        @render_bqplot
        def plot():
            x_sc = bqplot.LogScale()
            y_sc = bqplot.LinearScale()
            scatter = bqplot.Scatter(
                x=gap2007["gdpPercap"],
                y=gap2007["lifeExp"],
                scales={"x": x_sc, "y": y_sc},
                colors=["#4c78a8"],
                selected_style={"fill": "#e45756"},
                unselected_style={"opacity": 0.4},
            )
            return bqplot.Figure(
                marks=[scatter],
                axes=[
                    bqplot.Axis(scale=x_sc, label="GDP per capita"),
                    bqplot.Axis(scale=y_sc, orientation="vertical", label="Life expectancy"),
                ],
                interaction=interacts.LassoSelector(
                    x_scale=x_sc, y_scale=y_sc, marks=[scatter]
                ),
            )

    with ui.card():
        ui.card_header("Lassoed countries")

        @render.data_frame
        def table():
            # empty while nothing is lassoed, so it can be passed straight
            # to render.data_frame
            rows = plot.selected_rows(gap2007)
            return render.DataGrid(rows[["country", "lifeExp", "gdpPercap"]])
