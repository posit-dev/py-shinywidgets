import random

from perspective.widget import PerspectiveWidget
from shiny import reactive
from shiny.express import input, ui
from shinywidgets import render_widget

ui.input_action_button("add", "Add row")


def random_row(i: int):
    return {
        "id": i,
        "category": random.choice(["A", "B", "C"]),
        "value": round(random.random() * 100),
    }


@render_widget
def grid():
    return PerspectiveWidget(
        [random_row(i) for i in range(10)],
        plugin="Datagrid",
    )


@reactive.effect
@reactive.event(input.add)
def _():
    # PerspectiveWidget.update() streams a new row over the widget's comm,
    # so the grid updates in place (no full re-render)
    grid.widget.update([random_row(input.add() + 9)])
