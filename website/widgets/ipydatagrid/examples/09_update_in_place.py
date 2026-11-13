import pandas as pd
from ipydatagrid import DataGrid
from shiny import reactive
from shiny.express import input, render, ui
from shinywidgets import render_ipydatagrid

df = pd.DataFrame({"name": ["Ann", "Bo", "Cy", "Di", "Ev"], "score": [91, 72, 88, 65, 99]})
df2 = pd.DataFrame({"name": ["Fay", "Gus", "Hu"], "score": [55, 80, 70]})

ui.page_opts(fillable=True)
with ui.layout_columns(col_widths=[4, 4, 4]):
    ui.input_action_button("highlight", "Highlight top score")
    ui.input_action_button("sort", "Sort by score (desc)")
    ui.input_action_button("replace", "Replace data")

with ui.card(full_screen=True):

    @render_ipydatagrid
    def grid():
        return DataGrid(df.copy(), selection_mode="cell")


@reactive.effect
@reactive.event(input.highlight)
def _highlight():
    # Assign a new list -- DataGrid.select()/clear_selection() mutate the
    # existing list in place, so observers (including .selected()) never
    # see the change.
    top = int(grid.widget.data["score"].idxmax())
    grid.widget.selections = [{"r1": top, "r2": top, "c1": 0, "c2": 1}]


@reactive.effect
@reactive.event(input.sort)
def _sort():
    # Updates the grid's displayed order in place -- no re-render, so the
    # scroll position and the JS bundle are untouched.
    grid.widget.transform([{"type": "sort", "column": "score", "desc": True}])


@reactive.effect
@reactive.event(input.replace)
def _replace():
    with reactive.isolate():
        # Swapping `data` doesn't depend on anything reactive here, but
        # isolate() is the pattern to reach for once a handler also reads
        # other reactive widget state, to avoid re-triggering itself.
        grid.widget.data = df2


@render.text
def selected():
    return str(grid.selected())
