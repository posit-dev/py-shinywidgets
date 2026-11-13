# Title: Server file inspector
# One-line description: A fuller server-side file browser: sandboxed to a demo
#   project, with hidden-file and filter controls and bookmarked jump-to
#   locations. CSVs get a table + plot preview; everything else gets a text
#   snippet (or a "can't preview" message for binaries).
# Bucket: showcase
# Run with: uv run --with 'shinywidgets[ipyfilechooser,itables,plotly]' shiny run showcase_file_inspector.py
# Data source: plotly.express.data (gapminder, tips), written into a self-generating demo project

import os
import tempfile
from pathlib import Path

import pandas as pd
import plotly.express as px
from ipyfilechooser import FileChooser
from shiny import reactive, render, req
from shiny.express import input, ui
from shinywidgets import render_ipyfilechooser, render_itables, render_plotly


def make_project() -> Path:
    """A small demo project: data/, src/, notes/ (with a hidden draft)."""
    root = Path(tempfile.mkdtemp(prefix="shinywidgets-inspector-"))
    (root / "data").mkdir()
    (root / "src").mkdir()
    (root / "notes").mkdir()

    px.data.gapminder().to_csv(root / "data" / "gapminder.csv", index=False)
    px.data.tips().to_csv(root / "data" / "tips.csv", index=False)
    (root / "src" / "analysis.py").write_text(
        'import pandas as pd\n\ndf = pd.read_csv("data/gapminder.csv")\nprint(df.describe())\n'
    )
    (root / "notes" / "todo.md").write_text("# TODO\n\n- [x] try ipyfilechooser\n- [ ] ship it\n")
    (root / "notes" / ".draft.md").write_text(
        "# Draft\n\nToggle 'show hidden' in the sidebar to see this file.\n"
    )
    (root / "README.md").write_text(
        "# Demo project\n\nBrowse me with ipyfilechooser. Selections round-trip\n"
        "to Python, where this preview is built -- entirely on the server.\n"
    )
    return root


ROOT = make_project()
BOOKMARKS = {"project root": str(ROOT), "data/": str(ROOT / "data"), "src/": str(ROOT / "src")}

ui.page_opts(title="Server file inspector", fillable=True)

selection = reactive.value(str(ROOT / "README.md"))

with ui.sidebar(width=320):
    ui.input_select("jump", "Jump to", choices=list(BOOKMARKS))
    ui.input_checkbox("hidden", "Show hidden files", False)
    ui.input_select(
        "filter", "Filter", choices={"none": "all files", "csv": "*.csv", "py/md": "*.{py,md}"}
    )

    @render_ipyfilechooser
    def chooser():
        fc = FileChooser(
            path=str(ROOT), sandbox_path=str(ROOT), filename="README.md", select_default=True
        )
        # select_default=True shows README.md as selected but doesn't fire
        # the callback (only a user-confirmed pick does) -- `selection` is
        # pre-seeded above with that same default
        fc.register_callback(lambda fc: selection.set(fc.selected))
        return fc


@reactive.effect
@reactive.event(input.jump, ignore_init=True)
def _jump():
    # Clear the filename too: select_default=True re-applies a selection on
    # every reset(), and a stale "README.md" would otherwise carry over into
    # folders that don't have one
    chooser.widget.reset(path=BOOKMARKS[input.jump()], filename="")
    # reset() re-applies select_default's pick internally (fc.selected is
    # updated) but -- like any programmatic selection -- does not invoke
    # register_callback()'s callback, so mirror the new value ourselves
    selection.set(chooser.widget.selected)


@reactive.effect
def _hidden():
    chooser.widget.show_hidden = input.hidden()


@reactive.effect
def _filter():
    patterns = {"none": None, "csv": ["*.csv"], "py/md": ["*.py", "*.md"]}
    chooser.widget.filter_pattern = patterns[input.filter()]


@reactive.calc
def path() -> Path:
    req(selection())
    p = Path(selection())
    req(p.is_file())
    return p


@render.text
def title():
    sel = selection()
    if not sel:
        return "Pick a file"
    p = Path(sel)
    if not p.is_file():
        return f"{p.name} -- no such file here yet"
    return f"{p.name}  ({os.path.relpath(p, ROOT)})"


with ui.layout_columns(col_widths=(6, 6)):
    with ui.card(full_screen=True):
        ui.card_header("Table + plot (CSV files)")

        @render_itables
        def table():
            req(path().suffix == ".csv")
            return pd.read_csv(path())

        @render_plotly
        def plot():
            req(path().suffix == ".csv")
            df = pd.read_csv(path())
            if "lifeExp" in df.columns:
                return px.scatter(
                    df[df["year"] == 2007], x="gdpPercap", y="lifeExp",
                    size="pop", color="continent", log_x=True, hover_name="country",
                )
            return px.histogram(df, x="total_bill", color="sex")

    with ui.card(full_screen=True):
        ui.card_header("Text preview (everything else)")

        @render.code
        def preview():
            req(path().suffix != ".csv")
            try:
                return path().read_text()[:2000]
            except (OSError, UnicodeDecodeError) as e:
                return f"(can't preview this file: {e})"
