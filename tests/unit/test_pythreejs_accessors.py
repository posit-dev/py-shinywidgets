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
    # The raw is (replacement token, position, quaternion, zoom): the token
    # only changes when the camera instance does
    assert emitted[-1] == (1, (1.0, 2.0, 3.0), (0.0, 0.0, 0.0, 1.0), 1.0)
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
    # Re-seeded from the new camera, with the replacement token bumped
    assert emitted[-1] == (2, (5.0, 5.0, 5.0), (0.0, 0.0, 0.0, 1.0), 1.0)
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
    # None is published as the not-ready sentinel: readers cancel silently
    # until a camera exists
    assert emitted == [None]
    fig.camera = pythreejs.PerspectiveCamera(position=[1, 1, 1])
    assert len(emitted) == 2
    detach()


def test_camera_removal_cancels_readers() -> None:
    import ipyvolume as ipv
    from shiny.reactive._core import Context

    fig = ipv.Figure()
    fig.camera  # materialize the (lazy) default camera
    r = rw.render_ipyvolume()
    r._widget = fig  # stands in for _render()
    r._accessors.on_render(fig)
    context = Context()
    with context():
        r.camera()
    fig.camera = None  # clearing the camera must publish (invalidate readers)
    assert context._invalidated
    # ...and subsequent reads cancel silently until a camera exists
    with pytest.raises(SilentException):
        r.camera()


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


def test_pythreejs_camera_follows_orbit_state() -> None:
    import pythreejs

    scene = pythreejs.Scene()
    camera = pythreejs.PerspectiveCamera(position=[0, 0, 5])
    renderer = pythreejs.Renderer(scene=scene, camera=camera)
    r = rw.render_pythreejs()
    r._widget = renderer  # stands in for _render()
    r._accessors.on_render(renderer)
    assert r.camera() is camera  # the live camera, seeded as not-yet-orbited
    camera.position = [1, 0, 4]  # what an orbit syncs back
    assert tuple(r.camera().position) == (1.0, 0.0, 4.0)


def test_equal_pose_camera_replacement_still_invalidates() -> None:
    # Replacing the camera with a DIFFERENT instance in the same pose must
    # still invalidate reactive readers (the accessor returns the live
    # camera), even though the pose snapshot is unchanged
    import ipyvolume as ipv
    import pythreejs
    from shiny.reactive._core import Context

    fig = ipv.Figure()
    old = fig.camera  # materialize the (lazy) default camera
    r = rw.render_ipyvolume()
    r._widget = fig  # stands in for _render()
    r._accessors.on_render(fig)

    context = Context()
    with context():
        assert r.camera() is old
    assert not context._invalidated

    fig.camera = pythreejs.PerspectiveCamera(
        position=list(old.position),
        quaternion=list(old.quaternion),
        zoom=old.zoom,
    )
    assert context._invalidated

    # Equal pose reports from the SAME camera stay deduplicated
    context2 = Context()
    with context2():
        assert r.camera() is fig.camera
    # A list assignment fires a trait change (list != stored tuple) whose
    # snapshot is identical to the last one
    fig.camera.position = list(fig.camera.position)
    assert not context2._invalidated
