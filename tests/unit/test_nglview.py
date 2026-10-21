from __future__ import annotations

import asyncio
from types import ModuleType

import pytest
import shinywidgets
import shinywidgets._render_widget as rw
from shiny import Session
from shiny.express._stub_session import ExpressStubSession
from shiny.session import session_context

TINY_PDB = (
    "ATOM      1  N   ALA A   1      11.104   6.134  -6.504  1.00  0.00           N\n"
    "ATOM      2  CA  ALA A   1      11.639   6.071  -5.147  1.00  0.00           C\n"
    "END\n"
)


@pytest.fixture(scope="module")
def nglview() -> ModuleType:
    # nglview constructs a (global) widget when it's first imported, which
    # shinywidgets only tolerates inside a session.
    with session_context(ExpressStubSession()):
        nglview = pytest.importorskip("nglview")

    return nglview


def test_render_nglview_is_exported() -> None:
    assert shinywidgets.render_nglview is rw.render_nglview
    assert "render_nglview" in shinywidgets.__all__


def test_render_nglview_renders_widget_that_fills(
    nglview: ModuleType, widget_session: Session
) -> None:
    r = rw.render_nglview()

    @r
    def _():  # noqa: ANN202
        return nglview.show_text(TINY_PDB, ext="pdb")

    with session_context(widget_session):
        res = asyncio.run(r._render())

    assert res is not None
    assert res["widget_pkg"] == "nglview"
    assert res["fill"] is True
    assert isinstance(r.widget, nglview.NGLWidget)
