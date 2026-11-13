import plotly.express as px
from shiny.express import render, ui
from shinywidgets import render_plotly

df = px.data.gapminder().query("year == 2007").reset_index(drop=True)

ui.page_opts(title="Lasso some bubbles", fillable=True)

with ui.layout_columns(col_widths=[7, 5]):
    with ui.card(full_screen=True):

        @render_plotly
        def plot():
            fig = px.scatter(df, x="gdpPercap", y="lifeExp", color="continent", log_x=True)
            fig.update_layout(dragmode="lasso")
            return fig

    with ui.card():
        "plot.brushing() -- while dragging"

        @render.code
        def brushing_out():
            region = plot.brushing()
            return "None" if region is None else list(region.keys())[0]

        "plot.brushed() -- once the drag ends"

        @render.code
        def brushed_out():
            region = plot.brushed()
            if region is None:
                return "None (drag a lasso)"
            shape, coords = next(iter(region.items()))
            rounded = {axis: [round(v, 1) for v in vs] for axis, vs in coords.items()}
            return f"{shape}: {rounded}"
