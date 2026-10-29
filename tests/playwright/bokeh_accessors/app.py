from bokeh.models import ColumnDataSource
from bokeh.plotting import figure
from shiny.express import input, render, ui
from shinywidgets import render_bokeh


ui.input_action_button("rerender", "rerender")


@render_bokeh(height="400px")
def plot():
    input.rerender()
    src = ColumnDataSource({"x": [2, 5, 8], "y": [2, 5, 8], "name": list("abc")})
    p = figure(
        x_range=(0, 10),
        y_range=(0, 10),
        tools="tap,box_select,wheel_zoom",
        active_drag="box_select",
        active_scroll="wheel_zoom",
    )
    p.scatter("x", "y", source=src, size=20)
    return p


@render.text
def selected():
    return str(plot.selected())


@render.text
def selected_rows():
    return ",".join(plot.selected_rows()["name"])


@render.text
def tapped():
    t = plot.tapped()
    return "None" if t is None else f"{round(t.x)},{round(t.y)}"


@render.text
def zoomed():
    z = plot.zoomed()
    return "None" if z is None else "zoomed"
