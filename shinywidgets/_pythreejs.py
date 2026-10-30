"""
Accessors for `render_ipyvolume` and `render_pythreejs`, whose figures hold a
pythreejs `Camera` in their `camera` trait.

The raw value is an immutable snapshot tuple, never the camera itself: the
runtime's input priority treats `a is b` as equal, so emitting the same
mutable camera object each time would never publish (the accessor method
returns the live camera; see `render_ipyvolume.camera()`).
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, Callable, Dict, Optional, Tuple, cast

from ipywidgets.widgets.widget import Widget

from ._accessors import AccessorSpec, Emit

if TYPE_CHECKING:
    from pythreejs import Camera

CameraSnapshot = Tuple[Tuple[float, ...], Tuple[float, ...], float]


def camera_snapshot(camera: Camera) -> CameraSnapshot:
    # `zoom` exists on PerspectiveCamera/OrthographicCamera, not the base
    # Camera; three.js's default is 1
    return (
        tuple(camera.position),
        tuple(camera.quaternion),
        getattr(camera, "zoom", 1.0),
    )


def attach_camera(container: Widget, emit: Emit) -> Callable[[], None]:
    # (camera, handler) currently observed; None when the container's camera
    # is None (ipyvolume's trait allows it)
    inner: Optional[Tuple[Camera, Callable[[Dict[str, Any]], None]]] = None

    def detach_inner() -> None:
        nonlocal inner
        if inner is not None:
            camera, handler = inner
            camera.unobserve(handler, names=["position", "quaternion", "zoom"])
            inner = None

    def attach_inner(camera: Camera) -> None:
        nonlocal inner

        def on_camera_change(change: Dict[str, Any]) -> None:
            emit(camera_snapshot(camera))

        camera.observe(on_camera_change, names=["position", "quaternion", "zoom"])
        inner = (camera, on_camera_change)
        # Seed on every (re)attach, so readers see the current camera's state
        emit(camera_snapshot(camera))

    def on_container_change(change: Dict[str, Any]) -> None:
        detach_inner()
        if change["new"] is not None:
            attach_inner(change["new"])

    container.observe(on_container_change, names="camera")
    # `container` is an ipyvolume Figure or a pythreejs Renderer (both Widgets
    # with a `camera` trait); getattr keeps this free of those optional deps
    camera = cast(Optional["Camera"], getattr(container, "camera"))
    if camera is not None:
        attach_inner(camera)

    def detach() -> None:
        container.unobserve(on_container_change, names="camera")
        detach_inner()

    return detach


CAMERA = AccessorSpec(name="camera", kind="state", attach=attach_camera)
