from __future__ import annotations

import anywidget
import traitlets
from shiny import App, reactive, ui
from shinywidgets import output_widget, render_widget

app_ui = ui.page_fluid(
    ui.input_action_button("rerender", "Rerender"),
    output_widget("widget"),
)


class CleanupWidget(anywidget.AnyWidget):
    _esm = """
    export function render({ el }) {
      el.textContent = "anywidget content";
      // Observable synchronous cleanup (runs on view removal).
      return () => {
        window.anywidgetCleanups = (window.anywidgetCleanups || 0) + 1;
      };
    }
    """
    value = traitlets.Int(0).tag(sync=True)


class PendingCleanupWidget(anywidget.AnyWidget):
    _esm = """
    export function render({ el }) {
      el.textContent = "anywidget content";
      // A cleanup returning a promise that never settles: anywidget calls it
      // but never awaits it (upstream limit).
      return () => {
        window.anywidgetPendingCleanups = (window.anywidgetPendingCleanups || 0) + 1;
        return new Promise(() => {});
      };
    }
    """
    value = traitlets.Int(0).tag(sync=True)


def server(input, output, session):
    counter = reactive.value(0)

    @reactive.effect
    @reactive.event(input.rerender)
    def _():
        counter.set(counter.get() + 1)

    @render_widget
    def widget():
        n = counter.get()
        if n % 2 == 0:
            return CleanupWidget(value=n)
        return PendingCleanupWidget(value=n)


app = App(app_ui, server)
