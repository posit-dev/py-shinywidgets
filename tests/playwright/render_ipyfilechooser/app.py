from __future__ import annotations

import tempfile
from pathlib import Path

from ipyfilechooser import FileChooser
from ipywidgets import Layout
from shiny import App, reactive, render, ui
from shinywidgets import output_widget, render_ipyfilechooser

# A known directory for the choosers to browse
FIXTURE_DIR = Path(tempfile.mkdtemp(prefix="shinywidgets_ipyfilechooser_"))
(FIXTURE_DIR / "aaa.txt").write_text("hello\n")
(FIXTURE_DIR / "bbb.csv").write_text("x,y\n1,2\n")
(FIXTURE_DIR / "subdir").mkdir()

app_ui = ui.page_fluid(
    ui.input_action_button("rerender", "Rerender"),
    ui.output_text("render_count"),
    ui.card(
        ui.card_header("Default chooser"),
        output_widget("chooser"),
        style="height: 600px;",
    ),
    output_widget("wide"),
    ui.output_text("selected"),
)


def server(input, output, session):
    selection = reactive.value("none")

    @render.text
    def render_count():
        return str(input.rerender())

    @render_ipyfilechooser
    def chooser():
        input.rerender()
        fc = FileChooser(path=str(FIXTURE_DIR))
        # `selected` isn't a widget trait, so a callback (not reactive_read())
        # is the way to bring a confirmed selection into the reactive graph
        fc.register_callback(lambda fc: selection.set(fc.selected or "none"))
        return fc

    @render_ipyfilechooser
    def wide():
        return FileChooser(path=str(FIXTURE_DIR), layout=Layout(width="700px"))

    @render.text
    def selected():
        return selection.get()


app = App(app_ui, server)
