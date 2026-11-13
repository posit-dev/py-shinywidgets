import plotly.express as px
from shiny.express import input, render, ui
from shinywidgets import render_plotly

df = px.data.gapminder().query("year == 2007").reset_index(drop=True)

ui.page_opts(title="Lasso now, read later", fillable=True)

with ui.layout_columns(col_widths=[8, 4]):
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
            fig.update_layout(dragmode="lasso")
            return fig

    with ui.card():
        "Lasso some bubbles. Nothing reads the selection until you click Export."
        ui.input_action_button("export", "Export selection")

        @render.code
        def summary():
            if input.export() == 0:
                return "Nothing read yet."
            rows = plot.selected_rows(df)
            if rows.empty:
                return "No selection to export."
            return (
                f"{len(rows)} countries\n"
                f"mean life expectancy {rows['lifeExp'].mean():.1f} years"
            )
