# Read on demand: nothing in this app reads `plot.selected()` /
# `plot.selected_rows()` until the button's gated reader runs -- not a
# warm-up effect, not a visible output, nothing. Box- or lasso-select points
# FIRST, then click "Show selection": the selection you already made is
# there, because the accessor attached and started recording the moment the
# plot rendered, not on its first read. This is what makes a selection safe
# to read from a button handler, a `@reactive.event`-gated output, a
# download handler, or (see the ai-exploration article) a chat message
# handler or an LLM tool call -- any reader that only runs after the user
# has already interacted.
import plotly.express as px
from shiny import reactive
from shiny.express import input, render, ui
from shinywidgets import render_plotly

df = px.data.iris().reset_index(drop=True)

ui.page_opts(title="Read on demand", fillable=True)

with ui.layout_columns(col_widths=[7, 5]):
    with ui.card(full_screen=True):
        ui.card_header("Lasso or box-select points, THEN click the button")

        @render_plotly
        def plot():
            fig = px.scatter(
                df, x="sepal_width", y="sepal_length", custom_data=[df.index]
            )
            return fig.update_layout(dragmode="select")

    with ui.card():
        ui.input_action_button("show", "Show selection")
        ui.card_header("Only reads plot.selected_rows() once clicked")

        @render.data_frame
        @reactive.event(input.show)
        def selection_out():
            return render.DataGrid(plot.selected_rows(df))
