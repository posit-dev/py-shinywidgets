import plotly.express as px
from shiny import req
from shiny.express import render, ui
from shinywidgets import render_plotly

df = px.data.gapminder().query("year == 2007").reset_index(drop=True)

ui.page_opts(title="Gapminder 2007", fillable=True)

with ui.layout_columns():
    with ui.card(full_screen=True):
        ui.card_header("Lasso a few countries")

        @render_plotly
        def plot():
            fig = px.scatter(
                df,
                x="gdpPercap",
                y="lifeExp",
                size="pop",
                color="continent",
                size_max=48,
                hover_name="country",
                custom_data=[df.index],
                log_x=True,
                template="plotly_white",
            )
            fig.update_traces(marker=dict(opacity=0.85, line=dict(width=0)))
            fig.update_layout(dragmode="lasso", legend_title_text="")
            return fig

    with ui.card(full_screen=True):
        ui.card_header("Selected countries")

        @render.data_frame
        def selected_countries():
            rows = plot.selected_rows(df)
            req(not rows.empty)
            return rows[["country", "continent", "gdpPercap", "lifeExp", "pop"]]
