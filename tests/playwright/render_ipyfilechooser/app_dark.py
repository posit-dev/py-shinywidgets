from __future__ import annotations

import tempfile
from pathlib import Path

from ipyfilechooser import FileChooser
from shiny import App, ui
from shinywidgets import output_widget, render_ipyfilechooser

FIXTURE_DIR = Path(tempfile.mkdtemp(prefix="shinywidgets_ipyfilechooser_dark_"))

app_ui = ui.page_fluid(
    ui.input_dark_mode(mode="dark"),
    output_widget("chooser"),
)


def server(input, output, session):
    @render_ipyfilechooser
    def chooser():
        return FileChooser(path=str(FIXTURE_DIR))


app = App(app_ui, server)
