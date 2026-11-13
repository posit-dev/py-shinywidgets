import plotly.express as px
from plotly.subplots import make_subplots
from shiny.express import ui
from shinywidgets import render_plotly

df = px.data.stocks()

ui.page_opts(title="Stocks", fillable=True)


@render_plotly
def combo():
    fig = make_subplots(specs=[[{"secondary_y": True}]])
    fig.add_scatter(x=df["date"], y=df["GOOG"], name="GOOG", secondary_y=False)
    fig.add_bar(
        x=df["date"],
        y=df["GOOG"].diff(),
        name="day/day change",
        secondary_y=True,
        opacity=0.3,
    )
    fig.update_yaxes(title_text="price (normalized)", secondary_y=False)
    fig.update_yaxes(title_text="change", secondary_y=True)
    return fig
