from __future__ import annotations

import ipyreact
from shiny import App, render, ui
from shinywidgets import output_widget, reactive_read, render_widget


class CounterButton(ipyreact.ValueWidget):
    """An app-defined subclass, whose widget_pkg() is this app's module."""

    _esm = """
    import * as React from "react";

    export default function ({ value, setValue }) {
      return (
        <button onClick={() => setValue(value + 1)}>Clicked {value} times</button>
      );
    }
    """


app_ui = ui.page_fluid(
    output_widget("counter"),
    ui.output_text("value"),
)


def server(input, output, session):
    @render_widget
    def counter():
        return CounterButton(value=0)

    @render.text
    def value():
        return str(reactive_read(counter.widget, "value"))


app = App(app_ui, server)
