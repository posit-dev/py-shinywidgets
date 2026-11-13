import plotly.express as px
from shiny.express import render, ui
from shinywidgets import render_plotly

df = px.data.gapminder().query("year == 2007").reset_index(drop=True)

ui.page_opts(title="Click a bubble", fillable=True)

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
                custom_data=[df.index],
            )
            return fig

    with ui.card():
        ui.card_header("plot.clicked()")

        @render.code
        def clicked_out():
            pts = plot.clicked()
            if pts is None:
                return "None (click a bubble)"
            return pts.round(1).to_string(index=False)
