import altair as alt
import pandas as pd
from shiny.express import render
from shinywidgets import render_altair

dates = pd.DataFrame(
    {"date": pd.date_range("2024-01-01", periods=30, freq="D"), "y": range(30)}
)
values = pd.DataFrame({"v": [0.5, 1.2, 1.7, 2.0, 2.4, 3.3, 4.1]})


@render_altair(height="250px")
def brush_chart():
    brush = alt.selection_interval(name="brush", encodings=["x"])
    return alt.Chart(dates).mark_point().encode(x="date:T", y="y:Q").add_params(brush)


@render_altair(height="250px")
def bar_chart():
    pick = alt.selection_point(name="bar", encodings=["x"])
    return (
        alt.Chart(values)
        .mark_bar()
        .encode(alt.X("v:Q", bin=alt.Bin(step=1)), y="count()")
        .add_params(pick)
    )


@render.text
def brush_kind():
    return type(brush_chart.selected()).__name__


@render.text
def brushed_rows():
    return ",".join(str(y) for y in brush_chart.selected_rows()["y"])


@render.text
def bar_rows():
    return ",".join(str(v) for v in bar_chart.selected_rows()["v"])
