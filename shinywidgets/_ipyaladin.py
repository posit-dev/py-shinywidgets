"""
Accessors for `render_ipyaladin`.

`clicked_object()` is message-backed: ipyaladin registers its own custom
message handler via `on_msg`, so handlers the accessor adds through the same
dispatcher still fire (unlike ipyniivue, which overrides `_handle_custom_msg`;
see `_niivue.py`). The state accessors observe the widget's synced traits.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, Callable, Dict

from ._accessors import AccessorSpec, Attach, Emit

if TYPE_CHECKING:
    from ipyaladin import Aladin


def attach_object_clicked(widget: Aladin, emit: Emit) -> Callable[[], None]:
    def on_msg(_: object, content: object, _buffers: object) -> None:
        if isinstance(content, dict) and content.get("event_type") == "object_clicked":
            # Guard like the check above: ipywidgets swallows handler
            # exceptions silently, so a malformed message must not raise
            clicked = content.get("content")
            if clicked is not None:
                emit(clicked)

    widget.on_msg(on_msg)
    return lambda: widget.on_msg(on_msg, remove=True)


def observe_trait(name: str) -> Attach:
    def attach(widget: Aladin, emit: Emit) -> Callable[[], None]:
        def on_change(change: Dict[str, Any]) -> None:
            emit(change["new"])

        widget.observe(on_change, names=name)
        # Seed with the current value, so readers see the state from mount
        emit(getattr(widget, name))
        return lambda: widget.unobserve(on_change, names=name)

    return attach


CLICKED_OBJECT = AccessorSpec(
    name="clicked_object", kind="event", attach=attach_object_clicked
)
SELECTED_OBJECTS = AccessorSpec(
    name="selected_objects", kind="state", attach=observe_trait("_selected_objects")
)
TARGET = AccessorSpec(name="target", kind="state", attach=observe_trait("_target"))
FOV = AccessorSpec(name="fov", kind="state", attach=observe_trait("_fov"))

IPYALADIN_ACCESSORS = (CLICKED_OBJECT, SELECTED_OBJECTS, TARGET, FOV)
