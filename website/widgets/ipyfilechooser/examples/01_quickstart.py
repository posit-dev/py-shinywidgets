import os
import tempfile

from ipyfilechooser import FileChooser
from shiny import reactive, render
from shiny.express import ui
from shinywidgets import render_ipyfilechooser

def make_sample_dir() -> str:
    """A couple of sample files to browse (created fresh each run)."""
    data_dir = tempfile.mkdtemp(prefix="shinywidgets-quickstart-")
    for name in ("notes.txt", "report.csv"):
        with open(os.path.join(data_dir, name), "w") as f:
            f.write(f"sample contents of {name}\n")
    return data_dir


DATA_DIR = make_sample_dir()

ui.page_opts(title="ipyfilechooser quickstart")

selected_path = reactive.value(None)

with ui.card():

    @render_ipyfilechooser
    def chooser():
        fc = FileChooser(path=DATA_DIR)
        # `selected` is a plain property, not a trait: a callback -- not
        # reactive_read() -- is how a confirmed pick reaches Python
        fc.register_callback(lambda fc: selected_path.set(fc.selected))
        return fc

    @render.text
    def selected():
        return f"Selected: {selected_path()}"
