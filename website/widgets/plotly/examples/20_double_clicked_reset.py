import plotly.express as px
import plotly.graph_objects as go
from shiny import reactive, req
from shiny.express import ui
from shinywidgets import render_plotly

df = px.data.gapminder().query("year == 2007").reset_index(drop=True)
top15 = df.nlargest(15, "pop").sort_values("pop")

ui.page_opts(title="Click a bubble, double-click to reset", fillable=True)

with ui.layout_columns(col_widths=[7, 5]):
    with ui.card(full_screen=True):

        @render_plotly
        def scatter():
            return px.scatter(
                df,
                x="gdpPercap",
                y="lifeExp",
                color="continent",
                log_x=True,
                custom_data=[df.index],
            )

    with ui.card(full_screen=True):

        @render_plotly
        def bars():
            fig = go.Figure(go.Bar(x=top15["pop"], y=top15["country"], orientation="h"))
            fig.update_traces(marker_color="lightgray")
            return fig


@reactive.effect
def _highlight():
    pts = scatter.clicked()
    req(pts is not None)
    country = df.loc[pts["customdata"].iloc[0][0], "country"]
    with bars.widget.batch_update():
        for trace in bars.widget.data:
            trace.marker.color = [
                "#1f77b4" if c == country else "lightgray" for c in top15["country"]
            ]


# clicked() already clears itself on a background double-click, but that only
# resets scatter's own reader. double_clicked() is the general "the user
# reset the view" pulse -- reach for it when a *different* widget needs to
# react to a reset, including on subplot types (mapbox, ternary) where
# relayout()'s axis-range filter never reports one.
@reactive.effect
def _reset_bars():
    req(scatter.double_clicked())
    with reactive.isolate(), bars.widget.batch_update():
        for trace in bars.widget.data:
            trace.marker.color = "lightgray"
