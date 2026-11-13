from bokeh.models import ColumnDataSource
from bokeh.plotting import figure
from shiny.express import render, ui
from shinywidgets import render_bokeh

ui.page_opts(title="selected()", fillable=True)

src = ColumnDataSource(
    {"x": [1, 2, 3, 4, 5], "y": [2, 4, 1, 3, 5], "name": list("abcde")}
)

with ui.layout_columns(col_widths=[8, 4]):
    with ui.card(full_screen=True):

        @render_bokeh
        def plot():
            p = figure(
                x_range=(0, 6),
                y_range=(0, 6),
                tools="tap,box_select,lasso_select",
                active_drag="box_select",
                title="Tap, box, or lasso",
            )
            p.scatter("x", "y", source=src, size=20)
            return p

    with ui.card():
        ui.card_header("plot.selected()")

        @render.code
        def selected():
            return str(plot.selected())
