import plotly.express as px
from shiny.express import render, ui
from shinywidgets import render_plotly

df = px.data.gapminder().query("year == 2007").reset_index(drop=True)

ui.page_opts(title="Click for details", fillable=True)

with ui.layout_columns(col_widths=[8, 4]):
    with ui.card(full_screen=True):

        @render_plotly
        def plot():
            return px.scatter(
                df,
                x="gdpPercap",
                y="lifeExp",
                color="continent",
                log_x=True,
                size="pop",
                size_max=40,
                custom_data=[df.index],
            )

    with ui.card():

        @render.ui
        def detail():
            pts = plot.clicked()
            if pts is None:
                return ui.p("Click a bubble for details.", class_="text-muted")
            # px wraps each point's custom_data in a list; [0] is the row index.
            row = df.loc[pts["customdata"].iloc[0][0]]
            return ui.TagList(
                ui.h4(row["country"]),
                ui.p(f"Continent: {row['continent']}"),
                ui.p(f"Life expectancy: {row['lifeExp']:.1f} years"),
                ui.p(f"GDP per capita: ${row['gdpPercap']:,.0f}"),
                ui.p(f"Population: {row['pop']:,}"),
            )
