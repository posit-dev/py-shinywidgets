from __future__ import annotations

import ipywidgets
from shiny import App, Inputs, Outputs, Session, reactive, render, ui
from shinywidgets import output_widget, render_widget, session_lifetime
from shinywidgets._lifecycle import get_lifecycle

app_ui = ui.page_fluid(
    ui.input_select("dataset", "Dataset", ["A", "B"]),
    ui.input_action_button("bump", "Bump"),
    ui.input_action_button("fresh", "Fresh render"),
    ui.output_text("snapshot"),
    output_widget("cached"),
    output_widget("fresh_widget"),
)


def server(input: Inputs, output: Outputs, session: Session) -> None:
    cache: dict[str, ipywidgets.HTML] = {}
    fresh_count = reactive.value(0)

    @reactive.effect
    @reactive.event(input.bump)
    def _():
        # Update the currently displayed widget through its Python object.
        key = input.dataset()
        if key in cache:
            html = cache[key]
            count = int(html.value.split(":")[1]) + 1
            html.value = f"{key}:{count}"

    @reactive.effect
    @reactive.event(input.fresh)
    def _():
        fresh_count.set(fresh_count.get() + 1)

    @render_widget
    def cached() -> ipywidgets.HTML:
        key = input.dataset()
        if key not in cache:
            with session_lifetime():
                cache[key] = ipywidgets.HTML(value=f"{key}:0")
        return cache[key]

    @render_widget
    def fresh_widget() -> ipywidgets.HTML:
        n = fresh_count.get()
        return ipywidgets.HTML(value=f"fresh {n}")

    @reactive.poll(
        lambda: get_lifecycle(session.root_scope()).snapshot(),
        0.1,
    )
    def snapshot_values():
        return get_lifecycle(session.root_scope()).snapshot()

    @render.text
    def snapshot():
        snap = snapshot_values()
        return (
            f"records={snap.records} comms={snap.comms} "
            f"leases={snap.display_leases} pending={snap.pending_initializers}"
        )


app = App(app_ui, server)
