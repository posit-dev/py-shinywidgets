import random

import pandas as pd
from shiny import reactive
from shiny.express import input, render, ui
from shinywidgets import reactive_read, render_perspective

ui.input_action_button("add", "Add row")


def random_row(i: int):
    return {
        "id": i,
        "category": random.choice(["A", "B", "C"]),
        "value": round(random.random() * 100),
    }


@render_perspective
def grid():
    return pd.DataFrame([random_row(i) for i in range(10)])


@render.code
def viewer_state():
    # Changes made in the viewer's settings panel (sorting, grouping, filtering,
    # switching plugins, etc.) sync back to Python
    widget = grid.widget
    return str(
        {
            "plugin": reactive_read(widget, "plugin"),
            "group_by": reactive_read(widget, "group_by"),
            "sort": reactive_read(widget, "sort"),
            "filter": reactive_read(widget, "filter"),
        }
    )


@reactive.effect
@reactive.event(input.add)
def _():
    # PerspectiveWidget.update() streams a new row over the widget's comm,
    # so the grid updates in place (no full re-render)
    grid.widget.update([random_row(input.add() + 9)])
