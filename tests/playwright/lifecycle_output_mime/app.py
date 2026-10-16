from __future__ import annotations

import ipywidgets
from shiny import App, reactive, render, ui
from shinywidgets import output_widget, render_widget, session_lifetime
from shinywidgets._lifecycle import get_lifecycle

app_ui = ui.page_fluid(
    ui.input_action_button("clear", "Clear output"),
    ui.input_action_button("replace", "Replace content"),
    ui.input_action_button("drop", "Drop shared view"),
    ui.output_text("snapshot"),
    output_widget("out_widget"),
    ui.div(ui.output_ui("slot"), id="slot-holder"),
)


def snapshot_text(session) -> str:
    snap = get_lifecycle(session.root_scope()).snapshot()
    return (
        f"records={snap.records} comms={snap.comms} "
        f"leases={snap.display_leases} pending={snap.pending_initializers}"
    )


def server(input, output, session):
    counter = reactive.value(0)
    dropped = reactive.value(False)
    out = ipywidgets.Output()
    inner = ipywidgets.Output()
    shared_html: ipywidgets.HTML | None = None

    @reactive.effect
    @reactive.event(input.clear)
    def _():
        # ipywidgets' Output.clear_output() routes through the IPython kernel's
        # display system; outside a kernel the supported path is assigning
        # the outputs trait directly.
        out.outputs = ()

    @reactive.effect
    @reactive.event(input.replace)
    def _():
        counter.set(counter.get() + 1)
        n = counter.get()
        out.outputs = ()
        out.append_display_data(ipywidgets.HTML(value=f"nested content {n}"))
        inner.outputs = ()
        inner.append_display_data(ipywidgets.HTML(value=f"deep nested {n}"))
        out.append_display_data(inner)

    @reactive.effect
    @reactive.event(input.drop)
    def _():
        dropped.set(not dropped.get())

    @render_widget
    def out_widget():
        out.append_display_data(ipywidgets.HTML(value="nested content 0"))
        inner.append_display_data(ipywidgets.HTML(value="deep nested 0"))
        out.append_display_data(inner)
        return out

    @render.ui
    def slot():
        if dropped.get():
            return None
        return output_widget("shared")

    @render_widget
    def shared():
        nonlocal shared_html
        counter.get()
        if shared_html is None:
            with session_lifetime():
                shared_html = ipywidgets.HTML(value="shared root and mime")
            out.append_display_data(shared_html)
        return shared_html

    @reactive.poll(lambda: snapshot_text(session), 0.1)
    def snapshot_values() -> str:
        return snapshot_text(session)

    @render.text
    def snapshot():
        return snapshot_values()


app = App(app_ui, server)
