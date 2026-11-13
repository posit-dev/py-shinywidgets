import os
import tempfile

import pandas as pd
from ipyfilechooser import FileChooser
from shiny import reactive, render, req
from shiny.express import ui
from shinywidgets import render_ipyfilechooser


def make_project_dir() -> str:
    """A small project tree: a few subdirectories, each with a few files."""
    root = tempfile.mkdtemp(prefix="shinywidgets-project-")
    for sub, files in {
        "data": ["gapminder.csv", "tips.csv"],
        "notebooks": ["exploration.ipynb"],
        "src": ["app.py", "utils.py", "__init__.py"],
    }.items():
        os.makedirs(os.path.join(root, sub))
        for name in files:
            with open(os.path.join(root, sub, name), "w") as f:
                f.write(name * 20)  # a little bulk so sizes aren't all 0
    return root


PROJECT_DIR = make_project_dir()

ui.page_opts(title="Pick a directory, list its contents")

picked_dir = reactive.value(PROJECT_DIR)

with ui.card():

    @render_ipyfilechooser
    def dirpicker():
        fc = FileChooser(
            path=PROJECT_DIR,
            sandbox_path=PROJECT_DIR,
            show_only_dirs=True,
            title="Pick a subdirectory",
        )
        fc.register_callback(lambda fc: picked_dir.set(fc.selected_path))
        return fc

    @render.data_frame
    def contents():
        req(picked_dir())
        entries = []
        with os.scandir(picked_dir()) as it:
            for entry in it:
                entries.append(
                    {
                        "name": entry.name,
                        "kind": "dir" if entry.is_dir() else "file",
                        "size": entry.stat().st_size,
                    }
                )
        return pd.DataFrame(entries).sort_values(["kind", "name"])
