from __future__ import annotations

import pandas as pd
from ipydatagrid import DataGrid
from shiny import App, reactive, render, ui
from shinywidgets import output_widget, reactive_read, render_ipydatagrid

df = pd.DataFrame(
    {"id": range(1, 101), "letter": list("abcdefghij") * 10, "value": range(100, 200)}
)

app_ui = ui.page_fluid(
    ui.input_action_button("rerender", "Rerender"),
    ui.output_text("render_count"),
    ui.card(output_widget("grid"), height="400px", id="fill_card"),
    ui.output_text("selections"),
    output_widget("grid_fixed", height="250px"),
    output_widget("grid_fit_content_width", width="fit-content", height="250px"),
    output_widget("grid_widget_height"),
    output_widget("grid_auto", height="auto"),
)


def server(input, output, session):
    counter = reactive.value(0)

    @reactive.effect
    @reactive.event(input.rerender)
    def _():
        counter.set(counter.get() + 1)

    @render.text
    def render_count():
        return str(counter.get())

    @render_ipydatagrid
    def grid():
        counter.get()
        return DataGrid(df, selection_mode="cell")

    @render.text
    def selections():
        return str(reactive_read(grid.widget, "selections"))

    @render_ipydatagrid
    def grid_fixed():
        return df

    @render_ipydatagrid
    def grid_fit_content_width():
        return df

    @render_ipydatagrid
    def grid_widget_height():
        return DataGrid(df, layout={"height": "300px"})

    @render_ipydatagrid
    def grid_auto():
        return df


app = App(app_ui, server)
