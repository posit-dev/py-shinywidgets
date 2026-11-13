import plotly.express as px
import plotly.graph_objects as go
from shiny import reactive
from shiny.express import ui
from shinywidgets import render_plotly

df = px.data.gapminder().query("year == 2007").reset_index(drop=True)
top30 = df.nlargest(30, "pop").sort_values("pop")

ui.page_opts(title="Selection highlights a second plot", fillable=True)

with ui.layout_columns(col_widths=[7, 5]):
    with ui.card(full_screen=True):

        @render_plotly
        def scatter():
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

    with ui.card(full_screen=True):

        @render_plotly
        def bars():
            fig = go.Figure(go.Bar(x=top30["pop"], y=top30["country"], orientation="h"))
            fig.update_traces(marker_color="lightgray")
            return fig


@reactive.effect
def _highlight():
    selected = set(scatter.selected_rows(df)["country"])
    colors = ["#1f77b4" if c in selected else "lightgray" for c in top30["country"]]
    bars.widget.data[0].marker.color = colors
