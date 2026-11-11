"""
Accessors for `render_k3d`, backed by the plot's synced `camera` trait.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, Callable, Dict, Iterable, List, Sized, cast

from ._accessors import AccessorSpec, Emit

if TYPE_CHECKING:
    from k3d.plot import Plot


def attach_camera(widget: Plot, emit: Emit) -> Callable[[], None]:
    def on_change(change: Dict[str, Any]) -> None:
        emit(change["new"])

    widget.observe(on_change, names="camera")
    # Seed with the current value ([] until the browser auto-fits)
    emit(widget.camera)
    return lambda: widget.unobserve(on_change, names="camera")


def camera_not_ready(raw: object) -> bool:
    # The trait is ListOrArray: compare lengths, never `raw == []` (an
    # elementwise comparison error for numpy arrays)
    return len(cast(Sized, raw)) == 0


def camera_list(raw: object) -> List[float]:
    # The trait is ListOrArray; normalize so reads always get a list
    return list(cast(Iterable[float], raw))


CAMERA = AccessorSpec(
    name="camera",
    kind="state",
    attach=attach_camera,
    payload=camera_list,
    not_ready=camera_not_ready,
)
