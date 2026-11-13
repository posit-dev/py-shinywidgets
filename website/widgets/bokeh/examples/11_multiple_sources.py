from bokeh.layouts import row
from bokeh.models import ColumnDataSource
from bokeh.plotting import figure
from shiny import reactive
from shiny.express import render, ui
from shinywidgets import render_bokeh

ui.page_opts(title="Several ColumnDataSources", fillable=True)

west = ColumnDataSource({"x": [1, 2, 3], "y": [1, 2, 1], "name": list("abc")})
east = ColumnDataSource({"x": [1, 2, 3], "y": [2, 1, 2], "name": list("def")})

# plot.selected() would raise TypeError here (two sources). Wire each
# source's own callback into a reactive.value instead.
picked = reactive.value(None)
west.selected.on_change("indices", lambda attr, old, new: picked.set(("west", new)))
east.selected.on_change("indices", lambda attr, old, new: picked.set(("east", new)))

with ui.layout_columns(col_widths=[8, 4]):
    with ui.card(full_screen=True):

        @render_bokeh
        def plot():
            left = figure(
                title="west",
                tools="tap,box_select",
                active_drag="box_select",
                x_range=(0, 4),
                y_range=(0, 3),
                sizing_mode="stretch_both",
            )
            left.scatter("x", "y", source=west, size=20)
            right = figure(
                title="east",
                tools="tap,box_select",
                active_drag="box_select",
                x_range=(0, 4),
                y_range=(0, 3),
                sizing_mode="stretch_both",
            )
            right.scatter("x", "y", source=east, size=20, color="firebrick")
            return row(left, right, sizing_mode="stretch_both")

    with ui.card():
        ui.card_header("Last selection (either source)")

        @render.code
        def selection():
            return str(picked())
