import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from shiny import reactive, req
from shiny.express import input, render, ui
from shinywidgets import render_plotly

df = pd.DataFrame({"x": [1, 2, 3, 4, 5], "y": [1, 4, 9, 16, 25], "g": list("aabbb")})

ui.input_action_button("restyle", "restyle")


@render_plotly(listen_to=["selected", "hover"])
def plot():
    fig = px.scatter(df, x="x", y="y", color="g", custom_data=[df.index])
    fig.update_traces(marker_size=14)
    fig.update_layout(dragmode="select")
    return fig


# Updating the figure in place must not lose the bridge's event bindings.
@reactive.effect
@reactive.event(input.restyle)
def _():
    plot.widget.update_traces(marker_size=20)


ui.input_action_button("hide_b", "hide b")
ui.input_action_button("show_b", "show b")
ui.input_action_button("add_trace", "add trace")
ui.input_action_button("drop_trace", "drop trace")


# add_trace and trace removal go through Plotly.addTraces/deleteTraces,
# which redraw without a restyle or update: visible_traces() must follow
# them too
@reactive.effect
@reactive.event(input.add_trace)
def _():
    plot.widget.add_trace(go.Scatter(x=[3], y=[5], name="added"))


@reactive.effect
@reactive.event(input.drop_trace)
def _():
    # Assigning data diffs against the widget's traces and removes the rest
    plot.widget.data = [t for t in plot.widget.data if t.name != "added"]


# A batched update goes through Plotly.update (plotly_update), which
# visible_traces() must follow just like restyles
@reactive.effect
@reactive.event(input.hide_b)
def _():
    with plot.widget.batch_update():
        plot.widget.data[1].visible = False


@reactive.effect
@reactive.event(input.show_b)
def _():
    with plot.widget.batch_update():
        plot.widget.data[1].visible = True


@render.text
def clicked():
    pts = plot.clicked()
    if pts is None:
        return "None"
    return ";".join(
        f"{r.trace_index},{r.point_index},{r.x},{r.y}" for r in pts.itertuples()
    )


@render.text
def selected_rows():
    return ",".join(str(x) for x in plot.selected_rows(df)["x"])


@render.text
def brushed():
    b = plot.brushed()
    return "None" if b is None else ",".join(sorted(b))


@render.text
def relayout():
    r = plot.relayout()
    return "None" if r is None else ",".join(sorted(r))


@render.text
def hover():
    pts = plot.hover()
    if pts is None:
        return "None"
    return ";".join(
        f"{r.trace_index},{r.point_index},{r.x},{r.y}" for r in pts.itertuples()
    )


@render.text
def double_clicked():
    return "None" if plot.double_clicked() is None else "fired"


@render.text
def legend_clicked():
    traces = plot.legend_clicked()
    if traces is None:
        return "None"
    return ";".join(f"{r.trace_index},{r.name}" for r in traces.itertuples())


@render.text
def visible_traces():
    traces = plot.visible_traces()
    return "None" if traces is None else ",".join(str(v) for v in traces["visible"])


ui.input_action_button("late", "late")


# First read long after render, so its bind request reaches a live plot.
@render.text
def brushing():
    req(input.late())
    b = plot.brushing()
    return "None" if b is None else ",".join(sorted(b))


# A FigureWidget subclass defined in app code reports the app's module, not
# plotly, as its package
class AppFigure(go.FigureWidget):
    pass


@render_plotly
def sub_plot():
    fig = AppFigure(px.scatter(df, x="x", y="y"))
    fig.update_traces(marker_size=14)
    return fig


@render.text
def sub_clicked():
    pts = sub_plot.clicked()
    return "None" if pts is None else ";".join(str(x) for x in pts["x"])
