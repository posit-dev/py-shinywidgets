from __future__ import annotations

import asyncio

import pytest
import shinywidgets._render_widget as rw
import shinywidgets._render_widget_base as rwb
from shiny.session import session_context

# vizarr pins zarr<3, so it isn't in the shared test group; run these tests
# with `uv run --with vizarr pytest tests/unit/test_vizarr.py`
pytest.importorskip("vizarr", reason="vizarr isn't installed (it pins zarr<3)")

import numpy as np
import vizarr


def render_one(renderer: rwb.render_widget_base, value: object) -> dict[str, object]:

    @renderer
    def _():  # noqa: ANN202
        return value

    return asyncio.run(renderer._render())  # type: ignore


def test_render_vizarr_is_render_widget_base() -> None:
    assert isinstance(rw.render_vizarr(), rwb.render_widget_base)


def test_render_vizarr_passes_viewer_through(widget_session) -> None:
    r = rw.render_vizarr()
    with session_context(widget_session):
        viewer = vizarr.Viewer()
        res = render_one(r, viewer)

    assert res is not None
    assert r.widget is viewer
    assert res["widget_pkg"] == "vizarr"
    # The viewer's `height` trait (default "500px") isn't an ipywidgets
    # Layout height, so the output fills its container (and flexes with it)
    assert res["fill"] is True


def test_render_vizarr_fill_after_layout_defaults(widget_session) -> None:
    with session_context(widget_session):
        _, fill = rwb.set_layout_defaults(vizarr.Viewer())
    assert fill is True


def test_add_image_ndarray_registers_in_memory_store(widget_session) -> None:
    with session_context(widget_session):
        viewer = vizarr.Viewer()
        arr = np.zeros((16, 16), dtype=np.uint8)
        viewer.add_image(source=arr, name="zeros")

    assert len(viewer._configs) == 1
    assert viewer._configs[0]["name"] == "zeros"
    # A non-URL source is replaced by a reference into the comm-served stores
    assert viewer._configs[0]["source"] == {"id": 0}
    assert len(viewer._store_paths) == 1


def test_add_image_url_stays_a_url(widget_session) -> None:
    with session_context(widget_session):
        viewer = vizarr.Viewer()
        viewer.add_image(source="https://example.com/img.zarr")

    # URL sources are fetched by the browser directly, not served over the comm
    assert viewer._configs[0]["source"] == "https://example.com/img.zarr"
    assert viewer._store_paths == []


def test_view_state_trait_roundtrips(widget_session) -> None:
    with session_context(widget_session):
        viewer = vizarr.Viewer()
        viewer.view_state = {"target": [1, 2], "zoom": 3.0}
        assert viewer.view_state == {"target": [1, 2], "zoom": 3.0}
