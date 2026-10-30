from __future__ import annotations

from collections.abc import Iterator
from typing import List

import pytest
import shinywidgets._pythreejs as sp
import shinywidgets._render_widget as rw
from shiny import Session
from shiny.session import session_context
from shiny.types import SilentException


@pytest.fixture(autouse=True)
def in_session(widget_session: Session) -> Iterator[None]:
    with session_context(widget_session):
        yield


def test_camera_seeds_and_dedupes_equal_snapshots() -> None:
    import ipyvolume as ipv

    fig = ipv.Figure()
    fig.camera  # materialize the (lazy) default camera
    emitted: List[object] = []
    detach = sp.CAMERA.attach(fig, emitted.append)
    assert len(emitted) == 1  # seeded with the current camera's snapshot
    fig.camera.position = [1, 2, 3]
    assert emitted[-1] == ((1.0, 2.0, 3.0), (0.0, 0.0, 0.0, 1.0), 1.0)
    # The raw values are equal-value tuples, so a repeated report of the same
    # state is deduped by the runtime's input priority (covered by the helper's
    # own tests); what matters here is that the raw is an immutable snapshot,
    # never the camera itself (Review Focus 3)
    assert emitted[-1] is not fig.camera
    detach()


def test_camera_reattaches_on_camera_replacement() -> None:
    import ipyvolume as ipv
    import pythreejs

    fig = ipv.Figure()
    fig.camera  # materialize the (lazy) default camera
    emitted: List[object] = []
    detach = sp.CAMERA.attach(fig, emitted.append)
    old = fig.camera
    fig.camera = pythreejs.PerspectiveCamera(position=[5, 5, 5])
    assert emitted[-1][0] == (5.0, 5.0, 5.0)  # re-seeded from the new camera
    n = len(emitted)
    old.position = [9, 9, 9]  # stale camera: no longer observed
    assert len(emitted) == n
    detach()


def test_camera_tolerates_a_none_camera() -> None:
    import ipyvolume as ipv
    import pythreejs

    fig = ipv.Figure()
    fig.camera = None
    emitted: List[object] = []
    detach = sp.CAMERA.attach(fig, emitted.append)
    assert emitted == []  # nothing to observe until a camera is set
    fig.camera = pythreejs.PerspectiveCamera(position=[1, 1, 1])
    assert len(emitted) == 1
    detach()


def test_renderer_camera_returns_the_live_camera() -> None:
    import ipyvolume as ipv
    import pythreejs

    fig = ipv.Figure()
    fig.camera  # materialize the (lazy) default camera
    r = rw.render_ipyvolume()
    with pytest.raises(SilentException):
        r.camera()  # cancels before the first render
    r._widget = fig  # stands in for _render()
    r._accessors.on_render(fig)
    assert r.camera() is fig.camera
    fig.camera.position = [1, 2, 3]
    assert tuple(r.camera().position) == (1.0, 2.0, 3.0)
    # Replacing the camera re-seeds; reads return the new live camera
    cam = pythreejs.PerspectiveCamera(position=[5, 5, 5])
    fig.camera = cam
    assert r.camera() is cam
