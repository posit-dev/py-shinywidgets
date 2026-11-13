import plotly.express as px
from shiny.express import ui
from shinywidgets import render_plotly

df = px.data.tips()

ui.page_opts(title="Tips by day", fillable=True)


@render_plotly
def facets():
    fig = px.scatter(
        df,
        x="total_bill",
        y="tip",
        color="sex",
        facet_col="day",
        trendline="ols",
    )
    fig.update_layout(showlegend=False)
    return fig
