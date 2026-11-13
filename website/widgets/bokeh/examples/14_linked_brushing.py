# Uses bokeh's own sample-data package (downloaded on first use):
#   pip install bokeh_sampledata
from bokeh.layouts import row
from bokeh.models import ColumnDataSource
from bokeh.plotting import figure
from bokeh.sampledata.autompg import autompg
from shiny.express import render, ui
from shinywidgets import render_bokeh

ui.page_opts(title="Linked brushing", fillable=True)

src = ColumnDataSource(autompg)

with ui.layout_columns(col_widths=[8, 4]):
    with ui.card(full_screen=True):

        @render_bokeh
        def plots():
            tools = "box_select,lasso_select,reset"
            left = figure(
                title="weight vs. mpg", tools=tools, active_drag="box_select",
                sizing_mode="stretch_both",
            )
            left.scatter("weight", "mpg", source=src, size=6, alpha=0.6)

            right = figure(
                title="horsepower vs. mpg", tools=tools, active_drag="box_select",
                sizing_mode="stretch_both",
            )
            right.scatter("hp", "mpg", source=src, size=6, alpha=0.6, color="firebrick")

            return row(left, right, sizing_mode="stretch_both")

    with ui.card():
        ui.card_header("Selection summary (Python)")

        @render.text
        def summary():
            rows = plots.selected_rows()
            if len(rows) == 0:
                return "Box- or lasso-select cars in either plot."
            return (
                f"{len(rows)} selected\n"
                f"mean mpg: {rows['mpg'].mean():.1f}\n"
                f"mean weight: {rows['weight'].mean():,.0f} lbs"
            )
