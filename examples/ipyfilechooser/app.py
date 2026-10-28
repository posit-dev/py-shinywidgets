from itertools import islice
from pathlib import Path

from ipyfilechooser import FileChooser
from shiny import App, reactive, render, ui
from shinywidgets import output_widget, render_ipyfilechooser

app_ui = ui.page_fluid(
    ui.h2("ipyfilechooser in Shiny"),
    ui.p(
        "Browse the files on the server and select one. File previews are "
        "limited to this app's own directory; try the sandboxed chooser below too."
    ),
    ui.card(
        ui.card_header("Pick a file"),
        output_widget("chooser"),
        ui.output_text("selected"),
    ),
    ui.card(
        ui.card_header("Sandboxed to this directory, Python files only"),
        output_widget("sandboxed"),
        ui.output_text("sandboxed_selected"),
    ),
)

APP_DIR = Path(__file__).parent


def read_first_lines(path: str | None, n: int = 5) -> str:
    if not path:
        return "No file selected yet"
    resolved = Path(path).resolve()
    # The first chooser is not sandboxed, so don't let it read just anywhere:
    # only preview files under this app's own directory
    if not resolved.is_relative_to(APP_DIR):
        return f"{path}\n\n(can't read: previews are limited to {APP_DIR})"
    try:
        with open(resolved) as f:
            lines = list(islice(f, n))  # up to n lines; shorter files are fine
        return f"{resolved}\n\n{''.join(lines)}"
    except OSError as e:
        return f"{resolved}\n\n(can't read: {e})"


def server(input, output, session):
    selection = reactive.value(None)
    # The sandboxed chooser starts with app.py selected (select_default=True),
    # but ipyfilechooser only calls register_callback() callbacks when the
    # *user* confirms a selection, so seed the reactive value with the default
    sandboxed_selection = reactive.value(str(APP_DIR / "app.py"))

    @render_ipyfilechooser
    def chooser():
        fc = FileChooser(path=str(APP_DIR))
        fc.register_callback(lambda fc: selection.set(fc.selected))
        return fc

    @render_ipyfilechooser
    def sandboxed():
        fc = FileChooser(
            path=str(APP_DIR),
            filename="app.py",
            sandbox_path=str(APP_DIR),
            filter_pattern=["*.py"],
            title="Pick a Python file",
            select_default=True,
        )
        fc.register_callback(lambda fc: sandboxed_selection.set(fc.selected))
        return fc

    @render.text
    def selected():
        return read_first_lines(selection())

    @render.text
    def sandboxed_selected():
        return read_first_lines(sandboxed_selection())


app = App(app_ui, server)
