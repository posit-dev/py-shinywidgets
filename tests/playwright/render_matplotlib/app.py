from __future__ import annotations

import matplotlib.pyplot as plt
from ipywidgets import Widget
from matplotlib.figure import Figure
from shiny import App, Inputs, Outputs, Session, reactive, render, ui
from shinywidgets import as_widget, output_widget, render_matplotlib, session_lifetime

app_ui = ui.page_fluid(
    ui.input_action_button("rerender", "Rerender"),
    ui.input_select("mode", "Mode", ["new", "cached", "empty", "error"]),
    ui.input_action_button("remove", "Remove output"),
    ui.input_action_button("restore", "Restore output"),
    ui.output_text("render_count"),
    ui.div(output_widget("mpl"), id="plot_host"),
)


def server(input: Inputs, output: Outputs, session: Session) -> None:
    counter = reactive.value(0)
    cached: Widget | None = None

    @reactive.effect
    @reactive.event(input.rerender)
    def _():
        counter.set(counter.get() + 1)

    @render.text
    def render_count():
        return str(counter.get())

    @reactive.effect
    @reactive.event(input.remove)
    def remove_output() -> None:
        ui.remove_ui("#mpl", immediate=True)

    @reactive.effect
    @reactive.event(input.restore)
    def restore_output() -> None:
        ui.insert_ui(
            output_widget("mpl"),
            selector="#plot_host",
            where="beforeEnd",
            immediate=True,
        )

    @render_matplotlib
    def mpl() -> Figure | Widget | None:
        nonlocal cached
        mode = input.mode()
        if mode == "empty":
            return None
        if mode == "error":
            raise RuntimeError("Requested matplotlib error")
        n = counter.get()
        if mode == "cached" and cached is not None:
            return cached
        fig, ax = plt.subplots()
        ax.plot([1, 2, 3], [n, n + 1, n + 2])
        if mode == "cached":
            with session_lifetime():
                cached = as_widget(fig)
            return cached
        return fig


app = App(app_ui, server)
