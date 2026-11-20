import plotly.express as px
from shiny.express import render, ui
from shinywidgets import render_plotly

df = px.data.gapminder().query("year == 2007").reset_index(drop=True)

ui.page_opts(title="Box-select some bubbles", fillable=True)

with ui.layout_columns(col_widths=[7, 5]):
    with ui.card(full_screen=True):

        @render_plotly(listen_to=["selected", "selecting"])
        def plot():
            fig = px.scatter(
                df,
                x="gdpPercap",
                y="lifeExp",
                color="continent",
                log_x=True,
                custom_data=[df.index],
            )
            fig.update_layout(dragmode="select")
            return fig

    with ui.card():
        "plot.selecting() -- while dragging"

        @render.code
        def selecting_out():
            pts = plot.selecting()
            return "None" if pts is None else f"{len(pts)} points"

        "plot.selected() -- once the drag ends"

        @render.code
        def selected_out():
            pts = plot.selected()
            if pts is None or pts.empty:
                return "None (drag a box)"
            # Selection frames are slim (no x/y): the coordinates live in
            # your own data -- here customdata carries the df.index labels.
            rows = df.loc[[cd[0] for cd in pts["customdata"]]]
            return rows[["country", "lifeExp", "gdpPercap"]].round(1).to_string(index=False)
