from __future__ import annotations

from perspective.widget import PerspectiveWidget
from shiny import App, reactive, render, ui
from shinywidgets import output_widget, render_widget


def make_row(i: int) -> dict[str, object]:
    return {"id": i, "name": f"row-{i}", "value": i * 10}


app_ui = ui.page_fluid(
    ui.input_action_button("rerender", "Rerender"),
    ui.input_action_button("add_row", "Add row"),
    ui.output_text("render_count"),
    output_widget("viewer"),
)


def server(input, output, session):
    counter = reactive.value(0)
    next_id = reactive.value(3)

    @reactive.effect
    @reactive.event(input.rerender)
    def _():
        counter.set(counter.get() + 1)

    @render.text
    def render_count():
        return str(counter.get())

    @render_widget
    def viewer():
        return PerspectiveWidget([make_row(i) for i in range(3)], plugin="Datagrid")

    @reactive.effect
    @reactive.event(input.add_row)
    def _():
        # PerspectiveWidget.update() streams the row to the browser over the
        # widget's comm, exercising server -> client sync without a re-render
        i = next_id.get()
        next_id.set(i + 1)
        viewer.widget.update([make_row(i)])


app = App(app_ui, server)
