from bokeh.models import ColumnDataSource
from bokeh.plotting import figure
from shiny.express import render, ui
from shinywidgets import render_bokeh

ui.page_opts(title="Rate limiting selected()", fillable=True)


def points():
    return ColumnDataSource({"x": [1, 2, 3, 4, 5], "y": [2, 4, 1, 3, 5]})


def scatter(title):
    p = figure(
        x_range=(0, 6),
        y_range=(0, 6),
        tools="box_select",
        active_drag="box_select",
        title=title,
    )
    p.scatter("x", "y", source=points(), size=20)
    return p


with ui.layout_columns():
    with ui.card(full_screen=True):

        @render_bokeh  # default: debounced 250ms
        def default_plot():
            return scatter("default (debounce 250ms)")

        @render.code
        def default_selected():
            return str(default_plot.selected())

    with ui.card(full_screen=True):

        @render_bokeh(rate_delay=0)  # report every change immediately
        def instant_plot():
            return scatter("rate_delay=0")

        @render.code
        def instant_selected():
            return str(instant_plot.selected())
