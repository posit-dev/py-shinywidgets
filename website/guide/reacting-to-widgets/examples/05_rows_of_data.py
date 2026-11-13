# selected_rows() turns "which points did the user select" into "which rows
# of MY data frame". Plotly (like most selection-reporting widgets) reports
# points of the figure, not rows of a data frame, so each point must carry
# its row's identity as `customdata` -- here, the pandas index, via
# `custom_data=[df.index]`. altair/bokeh/itables/reactable each have their
# own version of this contract; see their guides' `selected_rows()` sections.
import plotly.express as px
from shiny.express import render, ui
from shinywidgets import render_plotly

df = px.data.tips().reset_index(drop=True)

ui.page_opts(title="Rows of your data", fillable=True)

with ui.layout_columns(col_widths=[7, 5]):
    with ui.card(full_screen=True):

        @render_plotly
        def plot():
            fig = px.scatter(df, x="total_bill", y="tip", custom_data=[df.index])
            return fig.update_layout(dragmode="select")

    with ui.card():
        ui.card_header("plot.selected_rows(df) -- matched by df.index")

        @render.data_frame
        def selected():
            return render.DataGrid(plot.selected_rows(df))
