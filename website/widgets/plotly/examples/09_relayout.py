import plotly.express as px
from shiny.express import render, ui
from shinywidgets import render_plotly

df = px.data.gapminder().query("year == 2007").reset_index(drop=True)


def fmt(v: object) -> str:
    return f"{v:.1f}" if isinstance(v, float) else str(v)


ui.page_opts(title="Zoom in", fillable=True)

with ui.layout_columns(col_widths=[7, 5]):
    with ui.card(full_screen=True):

        @render_plotly
        def plot():
            return px.scatter(df, x="lifeExp", y="gdpPercap", color="continent")

    with ui.card():
        ui.card_header("plot.relayout()")

        @render.code
        def relayout_out():
            axes = plot.relayout()
            if axes is None:
                return "None (zoom or pan)"
            return "\n".join(f"{k}: {fmt(v)}" for k, v in axes.items())
