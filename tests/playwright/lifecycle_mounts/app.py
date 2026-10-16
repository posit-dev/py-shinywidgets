from __future__ import annotations

import asyncio

import ipywidgets
from shiny import App, reactive, render, ui
from shinywidgets import output_widget, render_widget, session_lifetime
from shinywidgets._lifecycle import get_lifecycle

app_ui = ui.page_fluid(
    ui.input_action_button("rerender", "Rerender"),
    ui.input_action_button("slow", "Slow then fast"),
    ui.input_action_button("drop", "Drop second view"),
    ui.output_text("snapshot"),
    output_widget("box"),
    output_widget("shared_a"),
    ui.div(ui.output_ui("slot"), id="slot-holder"),
)


def snapshot_text(session) -> str:
    lifecycle = get_lifecycle(session.root_scope())
    snap = lifecycle.snapshot()
    return (
        f"records={snap.records} comms={snap.comms} "
        f"leases={snap.display_leases} pending={snap.pending_initializers}"
    )


def server(input, output, session):
    counter = reactive.value(0)
    mode = reactive.value("normal")
    dropped = reactive.value(False)
    shared: ipywidgets.HTML | None = None

    @reactive.effect
    @reactive.event(input.rerender)
    def _():
        mode.set("normal")
        counter.set(counter.get() + 1)

    @reactive.effect
    @reactive.event(input.slow)
    def _():
        mode.set("slow-then-fast")
        counter.set(counter.get() + 1)

    @reactive.effect
    @reactive.event(input.drop)
    def _():
        dropped.set(not dropped.get())

    @render_widget
    async def box():
        n = counter.get()
        if mode.get() == "slow-then-fast" and n % 2 == 1:
            # A slow candidate that will be superseded by the next value.
            await asyncio.sleep(2)
        children = [ipywidgets.HTML(value=f"child {n}")]
        return ipywidgets.Box(children=children)

    @render_widget
    def shared_a():
        nonlocal shared
        counter.get()
        if shared is None:
            with session_lifetime():
                shared = ipywidgets.HTML(value="shared model")
        return shared

    @render.ui
    def slot():
        if dropped.get():
            return None
        return output_widget("shared_b")

    @render_widget
    def shared_b():
        counter.get()
        # The same session-retained model displayed in a second view.
        if shared_a.widget is None:
            return ipywidgets.HTML(value="pending")
        return shared_a.widget

    @reactive.poll(lambda: snapshot_text(session), 0.1)
    def snapshot_values() -> str:
        return snapshot_text(session)

    @render.text
    def snapshot():
        return snapshot_values()


app = App(app_ui, server)
