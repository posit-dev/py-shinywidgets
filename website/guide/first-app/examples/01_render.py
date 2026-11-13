import plotly.express as px
from shiny.express import ui
from shinywidgets import render_plotly

df = px.data.gapminder().query("year == 2007").reset_index(drop=True)

ui.page_opts(title="Gapminder 2007", fillable=True)


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
