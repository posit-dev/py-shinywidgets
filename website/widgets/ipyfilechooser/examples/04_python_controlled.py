import os
import tempfile

from ipyfilechooser import FileChooser
from shiny import reactive, render
from shiny.express import input, ui
from shinywidgets import render_ipyfilechooser


def make_project_dir() -> str:
    root = tempfile.mkdtemp(prefix="shinywidgets-controlled-")
    os.makedirs(os.path.join(root, "data"))
    os.makedirs(os.path.join(root, "src"))
    for name in ("data/gapminder.csv", "data/tips.csv", "src/app.py", "notes.md"):
        with open(os.path.join(root, name), "w") as f:
            f.write("sample\n")
    with open(os.path.join(root, ".env"), "w") as f:
        f.write("SECRET=shh\n")
    return root


ROOT = make_project_dir()
BOOKMARKS = {"root": ROOT, "data": os.path.join(ROOT, "data"), "src": os.path.join(ROOT, "src")}

ui.page_opts(title="Steering the chooser from Shiny inputs")

with ui.sidebar():
    ui.input_select("jump", "Jump to", choices=list(BOOKMARKS))
    ui.input_checkbox("hidden", "Show hidden files", False)
    ui.input_select(
        "filter", "Filter", choices={"none": "all files", "csv": "*.csv", "py": "*.py"}
    )

selected_path = reactive.value(None)

with ui.card():

    @render_ipyfilechooser
    def chooser():
        fc = FileChooser(path=ROOT, sandbox_path=ROOT)
        fc.register_callback(lambda fc: selected_path.set(fc.selected))
        return fc

    @render.text
    def selected():
        return f"Selected: {selected_path()}"


# Python -> browser: jump the chooser to a bookmarked folder. reset() clears
# any current selection, so clear the mirrored reactive.value too
@reactive.effect
def _jump():
    chooser.widget.reset(path=BOOKMARKS[input.jump()])
    selected_path.set(None)


# These setters refresh the chooser's listing in place -- no re-render, and
# the user's current path and any confirmed selection are left untouched
@reactive.effect
def _toggle_hidden():
    chooser.widget.show_hidden = input.hidden()


@reactive.effect
def _set_filter():
    f = input.filter()
    chooser.widget.filter_pattern = None if f == "none" else [f"*.{f}"]
