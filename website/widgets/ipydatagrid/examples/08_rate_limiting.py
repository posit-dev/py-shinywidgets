import pandas as pd
from ipydatagrid import DataGrid
from shiny import reactive
from shiny.express import render, ui
from shinywidgets import reactive_read, render_ipydatagrid

df = pd.DataFrame({"a": range(10), "b": range(10, 20)})

ui.page_opts(fillable=True)
ui.markdown(
    "`.selected()` debounces by default (0.25s), so dragging across many "
    "cells publishes once, after you stop moving. `reactive_read()` on the "
    "widget directly is **not** rate-limited unless you pass "
    "`rate_policy`/`rate_delay` to `@render_ipydatagrid`, at which point both "
    "follow the same setting."
)


@render_ipydatagrid
def grid():
    return DataGrid(df, selection_mode="row")


accessor_fires = reactive.value(0)
raw_fires = reactive.value(0)


@reactive.effect
def _count_accessor():
    grid.selected()
    # isolate(): reading accessor_fires without it would make this effect
    # depend on the value it's about to set, looping forever
    with reactive.isolate():
        accessor_fires.set(accessor_fires.get() + 1)


@reactive.effect
def _count_raw():
    reactive_read(grid.widget, "selections")
    with reactive.isolate():
        raw_fires.set(raw_fires.get() + 1)


@render.text
def accessor_count():
    return f"selected() fired: {accessor_fires.get()}"


@render.text
def raw_count():
    return f"reactive_read() fired: {raw_fires.get()}"
