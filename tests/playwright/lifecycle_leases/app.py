from __future__ import annotations

import ipywidgets
from shiny import App, reactive, render, ui
from shinywidgets import output_widget, render_widget, session_lifetime
from shinywidgets._lifecycle import get_lifecycle

app_ui = ui.page_fluid(
    ui.input_action_button("rerender", "Rerender"),
    ui.input_action_button("drop", "Drop UI"),
    ui.output_text("snapshot"),
    ui.div(ui.output_ui("slot"), id="slot-holder"),
)


def server(input, output, session):
    counter = reactive.value(0)
    dropped = reactive.value(False)
    built = reactive.value(0)
    cached: ipywidgets.HTML | None = None

    @reactive.effect
    @reactive.event(input.rerender)
    def _():
        counter.set(counter.get() + 1)

    @reactive.effect
    @reactive.event(input.drop)
    def _():
        dropped.set(not dropped.get())

    @render.ui
    def slot():
        if dropped.get():
            return None
        return output_widget("widget")

    @render_widget
    def widget():
        nonlocal cached
        counter.get()
        # The same session-retained root is redisplayed on every render.
        if cached is None:
            with session_lifetime():
                cached = ipywidgets.HTML(value="cached root")
        with reactive.isolate():
            built.set(built.get() + 1)
        return cached

    # Lease release is a browser round-trip after the replacement attaches,
    # so the snapshot is eventually consistent.
    @reactive.poll(lambda: get_lifecycle(session.root_scope()).snapshot(), 0.1)
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
