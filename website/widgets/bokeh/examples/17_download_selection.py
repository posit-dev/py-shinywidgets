from bokeh.models import ColumnDataSource
from bokeh.plotting import figure
from shiny.express import render, ui
from shinywidgets import render_bokeh

ui.page_opts(title="Reading an accessor on demand", fillable=True)

src = ColumnDataSource(
    {"x": [1, 2, 3, 4, 5], "y": [2, 4, 1, 3, 5], "name": list("abcde")}
)

with ui.layout_columns(col_widths=[8, 4]):
    with ui.card(full_screen=True):
        ui.card_header("Box-select some points, then download them -- no need to click anything first")

        @render_bokeh
        def plot():
            p = figure(
                x_range=(0, 6),
                y_range=(0, 6),
                tools="box_select",
                active_drag="box_select",
            )
            p.scatter("x", "y", source=src, size=20)
            return p

    with ui.card():

        @render.download_button(
            filename="selection.csv", label="Download selection as CSV"
        )
        def download():
            # plot.selected_rows() is live the moment the plot renders, so
            # this reads whatever is currently selected -- even if the
            # download handler itself has never run before.
            yield plot.selected_rows().to_csv(index=False)
