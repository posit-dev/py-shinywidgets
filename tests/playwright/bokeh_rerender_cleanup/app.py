from __future__ import annotations

from bokeh.plotting import figure
from shiny import App, reactive, render, ui
from shinywidgets import bokeh_dependency, output_widget, render_bokeh
from shinywidgets._lifecycle import get_lifecycle

app_ui = ui.page_fluid(
    ui.input_action_button("rerender", "Rerender"),
    ui.output_text("render_count"),
    ui.output_text("widget_snapshot"),
    output_widget("plot"),
    bokeh_dependency(),
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

    @reactive.poll(lambda: get_lifecycle(session.root_scope()).snapshot(), 0.1)
    def snapshot_values():
        return get_lifecycle(session.root_scope()).snapshot()

    @render.text
    def widget_snapshot():
        snap = snapshot_values()
        return f"records={snap.records} comms={snap.comms} leases={snap.display_leases}"

    @render_bokeh
    def plot():
        n = counter.get()
        p = figure(title=f"render {n}")
        p.line([1, 2, 3], [n, n + 1, n + 2], line_width=2)
        return p


app = App(app_ui, server)
