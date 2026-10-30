from __future__ import annotations

import asyncio
import subprocess
import sys

import pytest
import shinywidgets._render_widget as rw
import shinywidgets._render_widget_base as rwb
from shiny.session import session_context

pytest.importorskip("ipyfilechooser")


def test_import_ipyfilechooser_after_shinywidgets() -> None:
    # Importing ipyfilechooser constructs a module-level Layout (the mutable
    # default for FileChooser's `layout` argument), which must be tolerated
    # outside a Shiny session
    script = "import shinywidgets\nimport ipyfilechooser\n"
    subprocess.run([sys.executable, "-c", script], check=True)


def render_one(renderer: rwb.render_widget_base, value: object) -> dict[str, object]:
    @renderer
    def _():  # noqa: ANN202
        return value

    return asyncio.run(renderer._render())  # type: ignore


def test_render_ipyfilechooser_passes_chooser_through(widget_session) -> None:
    from ipyfilechooser import FileChooser

    r = rw.render_ipyfilechooser()
    with session_context(widget_session):
        chooser = FileChooser()
        res = render_one(r, chooser)

    assert res is not None
    assert r.widget is chooser
    assert res["widget_pkg"] == "ipyfilechooser"
    # The chooser is an input-like form control with a natural size, so the
    # output doesn't fill its container
    assert res["fill"] is False


def shared_default_layout():
    import inspect

    from ipyfilechooser import FileChooser

    return inspect.signature(FileChooser.__init__).parameters["layout"].default


def test_chooser_gets_own_layout(widget_session) -> None:
    import shinywidgets._shinywidgets as sw
    from ipyfilechooser import FileChooser

    with session_context(widget_session):
        chooser = FileChooser()
        other = FileChooser()

    # Each chooser gets its own Layout, not the import-time one ipyfilechooser
    # shares as FileChooser's default `layout` argument (which has no comm,
    # and would leak layout changes between choosers)
    shared = shared_default_layout()
    assert chooser.layout is not shared
    assert chooser.layout is not other.layout
    # ... but keeps the shared default's values
    assert chooser.layout.width == shared.width
    # ... and it belongs to this session, so the chooser passes the
    # foreign/closed-widget check and the layout's comm opens on flush
    assert chooser.layout._model_id in sw.SESSION_WIDGET_ID_MAP[widget_session.id]
    assert sw.foreign_or_closed_widget(chooser, widget_session) is None


def test_chooser_layout_mutations_dont_leak_between_choosers(widget_session) -> None:
    from ipyfilechooser import FileChooser

    with session_context(widget_session):
        chooser = FileChooser()
        other = FileChooser()
        chooser.layout.width = "700px"

    assert other.layout.width != "700px"


def test_chooser_user_supplied_layout_is_kept(widget_session) -> None:
    from ipyfilechooser import FileChooser
    from ipywidgets import Layout

    with session_context(widget_session):
        layout = Layout(width="700px")
        chooser = FileChooser(layout=layout)

    assert chooser.layout is layout
