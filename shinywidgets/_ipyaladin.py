"""
Accessors for `render_ipyaladin`.

All four accessors observe the widget's synced traits. ipyaladin's frontend
retains the last clicked catalog source in the synced `clicked_object` trait
(it `model.set`s it and calls `save_changes()` on every click, per model), so
`clicked_object()` seeds at attach like the other state accessors, and the
parallel `object_clicked` custom message the frontend also sends isn't
needed.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, Callable, Dict, Optional

from ._accessors import AccessorSpec, Attach, Emit

if TYPE_CHECKING:
    from ipyaladin import Aladin


def observe_trait(name: str) -> Attach:
    def attach(widget: Aladin, emit: Emit) -> Callable[[], None]:
        def on_change(change: Dict[str, Any]) -> None:
            emit(change["new"])

        widget.observe(on_change, names=name)
        # Seed with the current value, so readers see the state from mount
        emit(getattr(widget, name))
        return lambda: widget.unobserve(on_change, names=name)

    return attach


def none_if_no_click(raw: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    # The synced trait defaults to {} (no click yet); report it as None to
    # keep the "None until the first click" contract
    return raw or None


CLICKED_OBJECT = AccessorSpec(
    name="clicked_object",
    kind="state",
    attach=observe_trait("clicked_object"),
    payload=none_if_no_click,
)
SELECTED = AccessorSpec(
    name="selected", kind="state", attach=observe_trait("_selected_objects")
)
TARGET = AccessorSpec(name="target", kind="state", attach=observe_trait("_target"))
FOV = AccessorSpec(name="fov", kind="state", attach=observe_trait("_fov"))

IPYALADIN_ACCESSORS = (CLICKED_OBJECT, SELECTED, TARGET, FOV)
