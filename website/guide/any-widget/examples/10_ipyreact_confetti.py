import ipyreact
from shiny.express import render, ui
from shinywidgets import render_widget

# ipyreact's own idiom: write real JSX in `_esm`, and `setValue` is handed to
# the component as a prop that writes straight back to the widget's `value`
# trait (ValueWidget's one synced trait). No separate click handler plumbing
# -- this is the whole widget.
CONFETTI_ESM = """
import confetti from "https://esm.sh/canvas-confetti@1";
import * as React from "react";

export default function ({ value, setValue }) {
  return React.createElement(
    "button",
    { onClick: () => { confetti(); setValue((value || 0) + 1); } },
    `${value || 0} times confetti`
  );
}
"""


class ConfettiButton(ipyreact.ValueWidget):
    _esm = CONFETTI_ESM


ui.page_opts(title="ipyreact: JSX widgets with no JS build step", fillable=True)

with ui.card():
    ui.card_header("ipyreact.ValueWidget subclass")

    @render_widget
    def button():
        return ConfettiButton()

    @render.code
    def count_out():
        n = button.read("value")
        return f"confetti fired {n or 0} time(s)"
