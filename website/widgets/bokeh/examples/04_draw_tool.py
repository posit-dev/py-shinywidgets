from bokeh.models import ColumnDataSource, PointDrawTool
from bokeh.plotting import figure
from shiny import reactive
from shiny.express import render, ui
from shinywidgets import render_bokeh

ui.page_opts(title="Editable plot", fillable=True)

edits = reactive.value(0)
src = ColumnDataSource({"x": [1, 2, 3], "y": [1, 2, 1]})
src.on_change("data", lambda attr, old, new: edits.set(edits() + 1))

with ui.layout_columns(col_widths=[8, 4]):
    with ui.card(full_screen=True):

        @render_bokeh
        def plot():
            p = figure(
                x_range=(0, 5), y_range=(0, 5), title="Drag points, or add new ones"
            )
            renderer = p.scatter("x", "y", source=src, size=15, color="firebrick")
            draw_tool = PointDrawTool(renderers=[renderer], add=True)
            p.add_tools(draw_tool)
            p.toolbar.active_tap = draw_tool
            return p

    with ui.card():
        ui.card_header("Current points (from Python)")

        @render.code
        def points():
            edits()  # re-run whenever the source's data changes
            return "\n".join(
                f"({x:.1f}, {y:.1f})" for x, y in zip(src.data["x"], src.data["y"])
            )
